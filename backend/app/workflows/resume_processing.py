import logging
from typing import Dict, Any, List
from datetime import datetime
import traceback
import re

from app.services.nlp_service import NLPService
from app.services.vector_service import VectorService
from app.core.database import SessionLocal
from app.models.database import Resume, ProcessingLog

logger = logging.getLogger(__name__)

class ResumeProcessingWorkflow:
    def __init__(self):
        self.nlp_service = None
        self.vector_service = None

    async def initialize(self):
        """Initialize the workflow services"""
        try:
            self.nlp_service = NLPService()
            self.vector_service = VectorService()
            await self.vector_service.initialize()
            logger.info("Resume processing workflow initialized")
        except Exception as e:
            logger.warning(f"Workflow initialization partial failure: {e}")

    async def process_resume(self, resume_id: str, filename: str, raw_content: str) -> Dict[str, Any]:
        """Process a resume through simplified workflow"""
        start_time = datetime.utcnow()
        
        result = {
            "resume_id": resume_id,
            "filename": filename,
            "status": "processing",
            "errors": [],
            "processing_time": 0.0
        }
        
        db = SessionLocal()
        
        try:
            # Update status to processing
            resume = db.query(Resume).filter(Resume.id == resume_id).first()
            if resume:
                resume.processing_status = "processing"
                db.commit()
            
            # Step 1: Clean and process content
            processed_content = self._clean_content(raw_content)
            
            # Step 2: Extract skills (with fallback)
            skills = []
            if self.nlp_service:
                try:
                    skills = await self.nlp_service.extract_skills(processed_content)
                except Exception as e:
                    logger.warning(f"NLP skill extraction failed: {e}")
                    skills = self._extract_skills_fallback(processed_content)
            else:
                skills = self._extract_skills_fallback(processed_content)
            
            # Step 3: Extract experience (with fallback)
            experience_data = {}
            if self.nlp_service:
                try:
                    experience_data = await self.nlp_service.extract_experience(processed_content)
                except Exception as e:
                    logger.warning(f"NLP experience extraction failed: {e}")
                    experience_data = self._extract_experience_fallback(processed_content)
            else:
                experience_data = self._extract_experience_fallback(processed_content)
            
            # Step 4: Calculate quality score
            quality_score = self._calculate_basic_quality(processed_content, skills, experience_data)
            
            # Step 5: Generate embeddings (if service available)
            embedding_status = "pending"
            if self.vector_service:
                try:
                    metadata = {
                        "resume_id": resume_id,
                        "filename": filename,
                        "skills": skills,
                        "experience_level": experience_data.get("level", ""),
                    }
                    await self.vector_service.store_resume_embeddings(resume_id, processed_content, metadata)
                    embedding_status = "completed"
                except Exception as e:
                    logger.warning(f"Vector embedding failed: {e}")
                    result["errors"].append(f"Embedding generation failed: {e}")
                    embedding_status = "failed"
            
            # Step 6: Update database
            if resume:
                resume.processed_content = processed_content
                resume.extracted_skills = skills
                resume.experience_level = experience_data.get("level", "")
                resume.experience_years = experience_data.get("years", 0)
                resume.quality_score = quality_score
                resume.processing_status = "completed" if not result["errors"] else "partial"
                resume.embedding_status = embedding_status
                
                db.commit()
            
            # Log success
            processing_time = (datetime.utcnow() - start_time).total_seconds()
            log = ProcessingLog(
                entity_type="resume",
                entity_id=resume_id,
                operation="full_processing",
                status="success" if not result["errors"] else "partial_success",
                details={
                    "skills_count": len(skills),
                    "experience_level": experience_data.get("level", ""),
                    "quality_score": quality_score
                },
                processing_time=processing_time
            )
            db.add(log)
            db.commit()
            
            result["status"] = "completed"
            result["processing_time"] = processing_time
            
            logger.info(f"Resume {resume_id} processed successfully")
            
        except Exception as e:
            logger.error(f"Error processing resume {resume_id}: {e}")
            logger.error(traceback.format_exc())
            
            result["errors"].append(str(e))
            result["status"] = "failed"
            
            # Update resume status
            try:
                if resume:
                    resume.processing_status = "failed"
                    db.commit()
                
                # Log error
                processing_time = (datetime.utcnow() - start_time).total_seconds()
                log = ProcessingLog(
                    entity_type="resume",
                    entity_id=resume_id,
                    operation="full_processing",
                    status="failed",
                    error_message=str(e),
                    processing_time=processing_time
                )
                db.add(log)
                db.commit()
                
            except Exception as db_error:
                logger.error(f"Failed to log error to database: {db_error}")
        
        finally:
            db.close()
        
        return result

    def _clean_content(self, content: str) -> str:
        """Basic content cleaning"""
        # Remove extra whitespace
        content = re.sub(r'\s+', ' ', content)
        # Remove special characters but keep important ones
        content = re.sub(r'[^\w\s\-\.\@\(\)\+]', ' ', content)
        return content.strip()

    def _extract_skills_fallback(self, content: str) -> List[str]:
        """Fallback skill extraction using pattern matching"""
        common_skills = [
            'Python', 'Java', 'JavaScript', 'React', 'Node.js', 'SQL', 'AWS', 'Docker',
            'Kubernetes', 'Git', 'HTML', 'CSS', 'MongoDB', 'PostgreSQL', 'Linux',
            'Machine Learning', 'Deep Learning', 'TensorFlow', 'PyTorch', 'Pandas',
            'FastAPI', 'Django', 'Flask', 'Vue.js', 'Angular', 'TypeScript', 'GraphQL',
            'Redis', 'Elasticsearch', 'Jenkins', 'CI/CD', 'Terraform', 'Ansible',
            'Microservices', 'REST API', 'OAuth', 'JWT', 'NGINX', 'Apache', 'DevOps'
        ]
        
        found_skills = []
        content_lower = content.lower()
        
        for skill in common_skills:
            if skill.lower() in content_lower:
                found_skills.append(skill)
        
        return found_skills[:15]  # Limit to 15 skills

    def _extract_experience_fallback(self, content: str) -> Dict[str, Any]:
        """Fallback experience extraction using pattern matching"""
        content_lower = content.lower()
        
        # Try to find years of experience
        years = 0
        year_patterns = [
            r'(\d+)\+?\s*years?\s*of\s*experience',
            r'(\d+)\+?\s*years?\s*experience',
            r'experience\s*:\s*(\d+)\+?\s*years?',
        ]
        
        for pattern in year_patterns:
            matches = re.findall(pattern, content_lower)
            if matches:
                years = max(int(match) for match in matches if match.isdigit())
                break
        
        # Determine level based on years and keywords
        if years >= 7 or any(word in content_lower for word in ['senior', 'lead', 'principal', 'architect']):
            level = 'senior'
        elif years >= 3 or any(word in content_lower for word in ['mid-level', 'intermediate']):
            level = 'mid'
        else:
            level = 'entry'
        
        return {
            "years": years,
            "level": level,
            "positions": [],
            "companies": []
        }

    def _calculate_basic_quality(self, content: str, skills: List[str], experience_data: Dict[str, Any]) -> float:
        """Calculate basic resume quality score"""
        score = 0.0
        
        # Content length score (0-0.3)
        content_score = min(len(content) / 2000, 1.0) * 0.3
        score += content_score
        
        # Skills score (0-0.4)
        skills_score = min(len(skills) / 10, 1.0) * 0.4
        score += skills_score
        
        # Experience score (0-0.3)
        experience_years = experience_data.get("years", 0)
        experience_score = min(experience_years / 8, 1.0) * 0.3
        score += experience_score
        
        return round(min(score, 1.0), 2)
