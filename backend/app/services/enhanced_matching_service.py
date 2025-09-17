import logging
from typing import List, Dict, Any, Optional
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
import re

from app.services.vector_service import VectorService
from app.services.cache_service import CacheService
from app.core.database import get_db
from app.models.database import Job, Resume, JobResumeMatch
from app.core.config import settings

logger = logging.getLogger(__name__)

class EnhancedMatchingService:
    def __init__(self):
        self.vector_service = VectorService()
        self.cache_service = CacheService()

    async def initialize(self):
        """Initialize matching service"""
        try:
            await self.vector_service.initialize()
            await self.cache_service.initialize()
            logger.info("Enhanced matching service initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize enhanced matching service: {e}")
            # Don't raise - allow partial functionality

    async def find_advanced_matches(self, job_id: str, top_k: int = 20, filters: Optional[Dict] = None) -> List[Dict[str, Any]]:
        """Find matches using enhanced algorithms"""
        try:
            # Check cache first
            cache_key = f"matches:{job_id}:{top_k}:{hash(str(filters))}"
            if self.cache_service:
                cached_result = await self.cache_service.get(cache_key)
                if cached_result:
                    logger.info(f"Returning cached matches for job {job_id}")
                    return cached_result

            # Get job details
            db = next(get_db())
            job = db.query(Job).filter(Job.id == job_id).first()
            if not job:
                raise ValueError(f"Job {job_id} not found")

            # Create comprehensive search queries
            search_queries = [
                f"{job.title} {' '.join(job.required_skills or [])}",
                f"{job.experience_level} {' '.join(job.requirements or [])}",
                f"{job.department} {job.company}" if job.department else f"{job.company}"
            ]

            all_matches = {}
            
            # Search with multiple query strategies if vector service is available
            if self.vector_service:
                for i, query in enumerate(search_queries):
                    try:
                        results = await self.vector_service.search_similar_resumes(
                            query, top_k * 2, filters
                        )
                        
                        # Process results and calculate weighted scores
                        await self._process_search_results(results, all_matches, weight=1.0 - (i * 0.2))
                    except Exception as e:
                        logger.warning(f"Search query {i} failed: {e}")
                        
            # Fallback to database matching if no vector results
            if not all_matches:
                all_matches = await self._fallback_database_matching(job, top_k, filters, db)

            # Calculate final scores and rankings
            final_matches = await self._calculate_final_scores(job, all_matches, top_k)
            
            # Generate detailed explanations
            enhanced_matches = []
            for match in final_matches:
                explanation = self._generate_simple_explanation(job, match)
                match["detailed_explanation"] = explanation
                enhanced_matches.append(match)

            # Cache results
            if self.cache_service:
                await self.cache_service.set(cache_key, enhanced_matches, ttl=1800)  # 30 minutes
            
            # Save matches to database
            await self._save_matches_to_db(job_id, enhanced_matches)
            
            return enhanced_matches

        except Exception as e:
            logger.error(f"Error in advanced matching: {e}")
            raise
        finally:
            db.close()

    async def _fallback_database_matching(self, job: Job, top_k: int, filters: Optional[Dict], db) -> Dict[str, Any]:
        """Fallback database-based matching when vector search is not available"""
        try:
            query = db.query(Resume).filter(Resume.processing_status == "completed")
            
            # Apply filters
            if filters:
                if filters.get("experience_level"):
                    query = query.filter(Resume.experience_level == filters["experience_level"])
            
            resumes = query.limit(top_k * 2).all()  # Get more candidates for better selection
            
            matches = {}
            job_skills = set(skill.lower().strip() for skill in job.required_skills or [])
            
            for resume in resumes:
                resume_skills = set(skill.lower().strip() for skill in resume.extracted_skills or [])
                
                # Calculate skill overlap
                matched_skills = job_skills.intersection(resume_skills)
                skill_score = len(matched_skills) / len(job_skills) if job_skills else 0.5
                
                # Calculate experience match
                exp_score = self._calculate_experience_match_simple(
                    job.experience_level, resume.experience_level, resume.experience_years
                )
                
                # Combined score
                combined_score = (skill_score * 0.7) + (exp_score * 0.3)
                
                matches[str(resume.id)] = {
                    "resume_id": str(resume.id),
                    "filename": resume.filename,
                    "scores": [combined_score],
                    "relevant_chunks": [resume.processed_content or resume.original_content or ""],
                    "metadata": {
                        "resume_id": str(resume.id),
                        "filename": resume.filename,
                        "experience_level": resume.experience_level,
                        "skills": resume.extracted_skills or []
                    }
                }
            
            return matches
            
        except Exception as e:
            logger.error(f"Fallback matching failed: {e}")
            return {}

    async def _process_search_results(self, results: Dict[str, Any], all_matches: Dict, weight: float = 1.0):
        """Process search results and accumulate match scores"""
        try:
            if not results.get("documents") or not results["documents"][0]:
                return

            for doc, metadata, distance in zip(
                results["documents"][0],
                results["metadatas"][0],
                results["distances"][0]
            ):
                resume_id = metadata.get("resume_id")
                if resume_id:
                    similarity_score = max(0, (1 - distance)) * weight
                    
                    if resume_id not in all_matches:
                        all_matches[resume_id] = {
                            "resume_id": resume_id,
                            "filename": metadata.get("filename", "Unknown"),
                            "scores": [],
                            "relevant_chunks": [],
                            "metadata": metadata
                        }
                    
                    all_matches[resume_id]["scores"].append(similarity_score)
                    all_matches[resume_id]["relevant_chunks"].append(doc)
                    
        except Exception as e:
            logger.error(f"Error processing search results: {e}")

    async def _calculate_final_scores(self, job: Job, all_matches: Dict, top_k: int) -> List[Dict[str, Any]]:
        """Calculate comprehensive final scores"""
        try:
            final_matches = []
            
            for resume_data in all_matches.values():
                if not resume_data.get("scores"):
                    continue
                    
                scores = np.array(resume_data["scores"])
                
                # Multi-factor scoring
                base_score = np.mean(scores)
                max_score = np.max(scores)
                consistency_score = 1 - (np.std(scores) / (np.mean(scores) + 1e-8))
                
                # Weighted final score
                final_score = (
                    base_score * 0.4 +
                    max_score * 0.3 +
                    consistency_score * 0.3
                )
                
                # Skill matching analysis
                skill_match_score = await self._calculate_skill_match(
                    job.required_skills or [],
                    resume_data["relevant_chunks"]
                )
                
                # Experience level matching
                experience_match_score = self._calculate_experience_match_from_metadata(
                    job.experience_level,
                    resume_data.get("metadata", {})
                )
                
                # Combined final score
                combined_score = (
                    final_score * 0.4 +
                    skill_match_score * 0.35 +
                    experience_match_score * 0.25
                )
                
                matched_skills, missing_skills = self._extract_skill_matches(
                    job.required_skills or [],
                    resume_data["relevant_chunks"]
                )
                
                final_matches.append({
                    "resume_id": resume_data["resume_id"],
                    "filename": resume_data["filename"],
                    "overall_score": round(combined_score * 100, 2),
                    "skill_match_score": round(skill_match_score * 100, 2),
                    "experience_match_score": round(experience_match_score * 100, 2),
                    "matched_skills": matched_skills,
                    "missing_skills": missing_skills,
                    "confidence_level": self._determine_confidence_level(combined_score),
                    "recommendation": self._determine_recommendation(combined_score)
                })
            
            # Sort by score and return top_k
            final_matches.sort(key=lambda x: x["overall_score"], reverse=True)
            return final_matches[:top_k]
            
        except Exception as e:
            logger.error(f"Error calculating final scores: {e}")
            return []

    async def _calculate_skill_match(self, required_skills: List[str], resume_chunks: List[str]) -> float:
        """Calculate skill matching score"""
        if not required_skills:
            return 0.0
        
        resume_text = " ".join(resume_chunks).lower()
        matched_count = 0
        
        for skill in required_skills:
            skill_variations = [
                skill.lower(),
                skill.lower().replace('.', ''),
                skill.lower().replace(' ', ''),
                skill.lower().replace('-', ' ')
            ]
            
            if any(variation in resume_text for variation in skill_variations):
                matched_count += 1
        
        return matched_count / len(required_skills)

    def _calculate_experience_match_simple(self, required_level: str, resume_level: Optional[str], resume_years: Optional[int]) -> float:
        """Simple experience level matching"""
        level_hierarchy = {"entry": 1, "mid": 2, "senior": 3, "lead": 4}
        
        req_level_num = level_hierarchy.get(required_level.lower(), 2)
        res_level_num = level_hierarchy.get((resume_level or "entry").lower(), 1)
        
        # Consider years of experience
        years_score = 0.5
        if resume_years:
            if resume_years >= 7:
                years_score = 1.0
            elif resume_years >= 3:
                years_score = 0.8
            elif resume_years >= 1:
                years_score = 0.6
        
        # Combine level and years
        level_diff = abs(req_level_num - res_level_num)
        level_score = max(0, 1 - (level_diff * 0.3))
        
        return (level_score * 0.6) + (years_score * 0.4)

    def _calculate_experience_match_from_metadata(self, required_level: str, metadata: Dict) -> float:
        """Calculate experience match from metadata"""
        resume_level = metadata.get("experience_level")
        resume_years = metadata.get("experience_years", 0)
        
        return self._calculate_experience_match_simple(required_level, resume_level, resume_years)

    def _extract_skill_matches(self, required_skills: List[str], resume_chunks: List[str]) -> tuple:
        """Extract matched and missing skills"""
        resume_text = " ".join(resume_chunks).lower()
        matched = []
        
        for skill in required_skills:
            skill_variations = [
                skill.lower(),
                skill.lower().replace('.', ''),
                skill.lower().replace(' ', ''),
                skill.lower().replace('-', ' ')
            ]
            
            if any(variation in resume_text for variation in skill_variations):
                matched.append(skill)
        
        missing = [skill for skill in required_skills if skill not in matched]
        return matched, missing

    def _determine_confidence_level(self, score: float) -> str:
        """Determine confidence level based on score"""
        if score >= 0.8:
            return "high"
        elif score >= 0.6:
            return "medium"
        else:
            return "low"

    def _determine_recommendation(self, score: float) -> str:
        """Determine hiring recommendation"""
        if score >= 0.8:
            return "strongly_recommended"
        elif score >= 0.65:
            return "recommended"
        elif score >= 0.4:
            return "consider"
        else:
            return "not_recommended"

    def _generate_simple_explanation(self, job: Job, match: Dict[str, Any]) -> str:
        """Generate simple explanation without LLM"""
        try:
            matched_skills = match.get("matched_skills", [])
            missing_skills = match.get("missing_skills", [])
            overall_score = match.get("overall_score", 0)
            
            explanation_parts = []
            
            # Overall assessment
            if overall_score >= 80:
                explanation_parts.append("Excellent candidate match.")
            elif overall_score >= 65:
                explanation_parts.append("Strong candidate with good alignment.")
            elif overall_score >= 50:
                explanation_parts.append("Decent candidate worth considering.")
            else:
                explanation_parts.append("Limited match with requirements.")
            
            # Skills assessment
            if matched_skills:
                if len(matched_skills) > 5:
                    explanation_parts.append(f"Has strong technical skills including {', '.join(matched_skills[:3])} and {len(matched_skills)-3} others.")
                else:
                    explanation_parts.append(f"Possesses key skills: {', '.join(matched_skills)}.")
            
            # Gaps
            if missing_skills and len(missing_skills) <= 3:
                explanation_parts.append(f"May need development in: {', '.join(missing_skills)}.")
            elif missing_skills:
                explanation_parts.append(f"Some skill gaps identified in {len(missing_skills)} areas.")
            
            # Recommendation
            recommendation = match.get("recommendation", "").replace("_", " ")
            if recommendation == "strongly recommended":
                explanation_parts.append("Highly recommended for immediate consideration.")
            elif recommendation == "recommended":
                explanation_parts.append("Recommended for interview process.")
            elif recommendation == "consider":
                explanation_parts.append("Worth considering with some reservations.")
            else:
                explanation_parts.append("May not be the best fit for this role.")
            
            return " ".join(explanation_parts)
            
        except Exception as e:
            logger.error(f"Error generating explanation: {e}")
            return f"Candidate scored {match.get('overall_score', 0)}% match with {len(match.get('matched_skills', []))} matching skills."

    async def _save_matches_to_db(self, job_id: str, matches: List[Dict[str, Any]]):
        """Save match results to database"""
        try:
            db = next(get_db())
            
            # Clear existing matches for this job
            db.query(JobResumeMatch).filter(JobResumeMatch.job_id == job_id).delete()
            
            # Save new matches
            for match in matches:
                db_match = JobResumeMatch(
                    job_id=job_id,
                    resume_id=match["resume_id"],
                    overall_score=match["overall_score"],
                    skill_match_score=match["skill_match_score"],
                    experience_match_score=match["experience_match_score"],
                    matched_skills=match["matched_skills"],
                    missing_skills=match["missing_skills"],
                    explanation=match.get("detailed_explanation", ""),
                    confidence_level=match["confidence_level"],
                    recommendation=match["recommendation"]
                )
                db.add(db_match)
            
            db.commit()
            logger.info(f"Saved {len(matches)} matches for job {job_id}")
            
        except Exception as e:
            logger.error(f"Error saving matches to database: {e}")
            db.rollback()
        finally:
            db.close()

    async def get_match_analytics(self, job_id: str) -> Dict[str, Any]:
        """Get analytics for job matches"""
        try:
            db = next(get_db())
            matches = db.query(JobResumeMatch).filter(JobResumeMatch.job_id == job_id).all()
            
            if not matches:
                return {"message": "No matches found", "analytics": {}}
            
            scores = [match.overall_score for match in matches]
            recommendations = {}
            confidence_levels = {}
            
            for match in matches:
                recommendations[match.recommendation] = recommendations.get(match.recommendation, 0) + 1
                confidence_levels[match.confidence_level] = confidence_levels.get(match.confidence_level, 0) + 1
            
            analytics = {
                "total_matches": len(matches),
                "average_score": round(sum(scores) / len(scores), 2),
                "highest_score": max(scores),
                "lowest_score": min(scores),
                "score_distribution": {
                    "excellent": len([s for s in scores if s >= 80]),
                    "good": len([s for s in scores if 60 <= s < 80]),
                    "fair": len([s for s in scores if 40 <= s < 60]),
                    "poor": len([s for s in scores if s < 40])
                },
                "recommendations": recommendations,
                "confidence_levels": confidence_levels
            }
            
            return {"analytics": analytics}
            
        except Exception as e:
            logger.error(f"Error getting match analytics: {e}")
            return {"error": str(e)}
        finally:
            db.close()

    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on matching service"""
        try:
            vector_health = "unknown"
            cache_health = "unknown"
            
            if self.vector_service:
                vector_check = await self.vector_service.health_check()
                vector_health = vector_check.get("status", "unknown")
            
            if self.cache_service:
                cache_check = await self.cache_service.health_check()
                cache_health = cache_check.get("status", "unknown")
            
            return {
                "status": "healthy",
                "vector_service": vector_health,
                "cache_service": cache_health,
                "matching_algorithms": ["skill_matching", "experience_matching", "semantic_similarity"],
                "fallback_available": True
            }
            
        except Exception as e:
            logger.error(f"Matching service health check failed: {e}")
            return {"status": "unhealthy", "error": str(e)}
