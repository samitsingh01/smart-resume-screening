# backend/app/services/enhanced_matching_service.py
import logging
from typing import List, Dict, Any, Optional
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from app.services.aws_bedrock import BedrockLLM
from langchain.prompts import PromptTemplate

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
        self.llm = BedrockLLM(
            model_id="anthropic.claude-3-sonnet-20240229-v1:0",
            region_name=settings.aws_region,
            model_kwargs={"max_tokens": 2000, "temperature": 0.1}
        )

    async def initialize(self):
        """Initialize matching service"""
        try:
            await self.vector_service.initialize()
            await self.cache_service.initialize()
            logger.info("Enhanced matching service initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize enhanced matching service: {e}")
            raise

    async def find_advanced_matches(self, job_id: str, top_k: int = 20, filters: Optional[Dict] = None) -> List[Dict[str, Any]]:
        """Find matches using advanced algorithms"""
        try:
            # Check cache first
            cache_key = f"matches:{job_id}:{top_k}:{hash(str(filters))}"
            cached_result = await self.cache_service.get(cache_key)
            if cached_result:
                logger.info(f"Returning cached matches for job {job_id}")
                return cached_result

            # Get job details
            db = next(get_db())
            job = db.query(Job).filter(Job.id == job_id).first()
            if not job:
                raise ValueError(f"Job {job_id} not found")

            # Create comprehensive search query
            search_queries = [
                f"{job.title} {' '.join(job.required_skills)}",
                f"{job.experience_level} {' '.join(job.requirements)}",
                f"{job.department} {job.company}" if job.department else f"{job.company}"
            ]

            all_matches = {}
            
            # Search with multiple query strategies
            for i, query in enumerate(search_queries):
                results = await self.vector_service.search_similar_resumes(
                    query, top_k * 3, filters
                )
                
                # Process results and calculate weighted scores
                await self._process_search_results(results, all_matches, weight=1.0 - (i * 0.2))

            # Calculate final scores and rankings
            final_matches = await self._calculate_final_scores(job, all_matches, top_k)
            
            # Generate detailed explanations
            enhanced_matches = []
            for match in final_matches:
                explanation = await self._generate_detailed_explanation(job, match)
                match["detailed_explanation"] = explanation
                enhanced_matches.append(match)

            # Cache results
            await self.cache_service.set(cache_key, enhanced_matches, ttl=1800)  # 30 minutes
            
            # Save matches to database
            await self._save_matches_to_db(job_id, enhanced_matches)
            
            return enhanced_matches

        except Exception as e:
            logger.error(f"Error in advanced matching: {e}")
            raise
        finally:
            db.close()

    async def _process_search_results(self, results: Dict[str, Any], all_matches: Dict, weight: float = 1.0):
        """Process search results and accumulate match scores"""
        if not results.get("documents") or not results["documents"][0]:
            return

        for doc, metadata, distance in zip(
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0]
        ):
            resume_id = metadata["resume_id"]
            similarity_score = (1 - distance) * weight
            
            if resume_id not in all_matches:
                all_matches[resume_id] = {
                    "resume_id": resume_id,
                    "filename": metadata["filename"],
                    "scores": [],
                    "relevant_chunks": [],
                    "metadata": metadata
                }
            
            all_matches[resume_id]["scores"].append(similarity_score)
            all_matches[resume_id]["relevant_chunks"].append(doc)

    async def _calculate_final_scores(self, job: Job, all_matches: Dict, top_k: int) -> List[Dict[str, Any]]:
        """Calculate comprehensive final scores"""
        final_matches = []
        
        for resume_data in all_matches.values():
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
                job.required_skills,
                resume_data["relevant_chunks"]
            )
            
            # Experience level matching
            experience_match_score = await self._calculate_experience_match(
                job.experience_level,
                resume_data["relevant_chunks"]
            )
            
            # Combined final score
            combined_score = (
                final_score * 0.5 +
                skill_match_score * 0.3 +
                experience_match_score * 0.2
            )
            
            final_matches.append({
                "resume_id": resume_data["resume_id"],
                "filename": resume_data["filename"],
                "overall_score": round(combined_score * 100, 2),
                "skill_match_score": round(skill_match_score * 100, 2),
                "experience_match_score": round(experience_match_score * 100, 2),
                "matched_skills": await self._extract_matched_skills(
                    job.required_skills,
                    resume_data["relevant_chunks"]
                ),
                "missing_skills": await self._extract_missing_skills(
                    job.required_skills,
                    resume_data["relevant_chunks"]
                ),
                "confidence_level": self._determine_confidence_level(combined_score),
                "recommendation": self._determine_recommendation(combined_score)
            })
        
        # Sort by score and return top_k
        final_matches.sort(key=lambda x: x["overall_score"], reverse=True)
        return final_matches[:top_k]

    async def _calculate_skill_match(self, required_skills: List[str], resume_chunks: List[str]) -> float:
        """Calculate skill matching score"""
        if not required_skills:
            return 0.0
        
        resume_text = " ".join(resume_chunks).lower()
        matched_count = 0
        
        for skill in required_skills:
            if skill.lower() in resume_text:
                matched_count += 1
        
        return matched_count / len(required_skills)

    async def _calculate_experience_match(self, required_level: str, resume_chunks: List[str]) -> float:
        """Calculate experience level matching score"""
        experience_keywords = {
            "entry": ["junior", "entry", "associate", "trainee", "intern", "graduate", "fresher"],
            "mid": ["mid", "intermediate", "experienced", "specialist", "developer", "analyst"],
            "senior": ["senior", "lead", "principal", "expert", "architect", "manager", "director"],
            "lead": ["lead", "principal", "director", "manager", "head", "chief", "vp", "vice president"]
        }
        
        resume_text = " ".join(resume_chunks).lower()
        required_keywords = experience_keywords.get(required_level.lower(), [])
        
        if not required_keywords:
            return 0.5  # Neutral score if level not recognized
        
        match_count = sum(1 for keyword in required_keywords if keyword in resume_text)
        return min(match_count / len(required_keywords), 1.0)

    async def _extract_matched_skills(self, required_skills: List[str], resume_chunks: List[str]) -> List[str]:
        """Extract skills that are present in both job and resume"""
        resume_text = " ".join(resume_chunks).lower()
        matched = []
        
        for skill in required_skills:
            # Check for exact match or partial match
            skill_lower = skill.lower()
            if skill_lower in resume_text:
                matched.append(skill)
            # Check for common variations
            elif any(variation in resume_text for variation in [
                skill_lower.replace('.', ''),
                skill_lower.replace(' ', ''),
                skill_lower.replace('-', ' '),
                skill_lower.replace('_', ' ')
            ]):
                matched.append(skill)
        
        return matched

    async def _extract_missing_skills(self, required_skills: List[str], resume_chunks: List[str]) -> List[str]:
        """Extract skills that are missing from resume"""
        matched_skills = await self._extract_matched_skills(required_skills, resume_chunks)
        return [skill for skill in required_skills if skill not in matched_skills]

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
        elif score >= 0.5:
            return "consider"
        else:
            return "not_recommended"

    async def _generate_detailed_explanation(self, job: Job, match: Dict[str, Any]) -> str:
        """Generate detailed explanation using advanced LLM"""
        prompt = PromptTemplate(
            input_variables=["job_title", "job_requirements", "job_skills", "overall_score", "skill_match_score", "experience_match_score", "matched_skills", "missing_skills"],
            template="""
            As an expert HR analyst, provide a detailed assessment of this candidate match:
            
            Job Position: {job_title}
            Requirements: {job_requirements}
            Required Skills: {job_skills}
            
            Candidate Assessment:
            - Overall Match Score: {overall_score}%
            - Skill Match Score: {skill_match_score}%
            - Experience Match Score: {experience_match_score}%
            - Matched Skills: {matched_skills}
            - Missing Skills: {missing_skills}
            
            Provide a comprehensive 3-4 sentence analysis covering:
            1. Key strengths of this candidate for this role
            2. Areas where they excel and align with requirements
            3. Potential concerns or skill gaps to consider
            4. Overall hiring recommendation with rationale
            
            Be specific, actionable, and professional in your assessment.
            """
        )
        
        try:
            formatted_prompt = prompt.format(
                job_title=job.title,
                job_requirements=", ".join(job.requirements) if job.requirements else "None specified",
                job_skills=", ".join(job.required_skills) if job.required_skills else "None specified",
                overall_score=match["overall_score"],
                skill_match_score=match["skill_match_score"],
                experience_match_score=match["experience_match_score"],
                matched_skills=", ".join(match["matched_skills"]) if match["matched_skills"] else "None",
                missing_skills=", ".join(match["missing_skills"]) if match["missing_skills"] else "None"
            )
            
            explanation = await self.llm.ainvoke(formatted_prompt)
            return explanation.strip()
            
        except Exception as e:
            logger.error(f"Error generating detailed explanation: {e}")
            # Fallback explanation
            matched_skills_str = ", ".join(match["matched_skills"][:3]) if match["matched_skills"] else "some relevant skills"
            return f"Strong candidate with {match['overall_score']}% overall match. Key strengths include {matched_skills_str}. Skill alignment at {match['skill_match_score']}% with experience level matching at {match['experience_match_score']}%. Recommend for {match['recommendation'].replace('_', ' ')} consideration."

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
            # Test LLM connection
            test_response = await self.llm.ainvoke("Say 'test' in one word.")
            
            # Test vector service
            vector_health = await self.vector_service.health_check()
            
            return {
                "status": "healthy",
                "llm_model": self.llm.model_id,
                "test_response": test_response[:20] if test_response else "No response",
                "vector_service": vector_health.get("status", "unknown"),
                "cache_service": "healthy" if self.cache_service.redis_client else "unavailable"
            }
            
        except Exception as e:
            logger.error(f"Matching service health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e)
            }
