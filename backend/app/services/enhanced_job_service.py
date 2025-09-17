import logging
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from app.models.database import Job, ProcessingLog
from app.services.vector_service import VectorService
from app.services.cache_service import CacheService
from app.core.config import settings

logger = logging.getLogger(__name__)

class EnhancedJobService:
    def __init__(self):
        self.vector_service = VectorService()
        self.cache_service = CacheService()

    async def initialize(self):
        """Initialize enhanced job service"""
        try:
            await self.vector_service.initialize()
            await self.cache_service.initialize()
            logger.info("Enhanced job service initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize enhanced job service: {e}")
            # Don't raise - allow partial functionality

    async def create_job_enhanced(self, job_data: Dict[str, Any], db: Session) -> str:
        """Create job with enhanced processing"""
        try:
            job_id = str(uuid.uuid4())
            
            job = Job(
                id=job_id,
                title=job_data["title"],
                company=job_data["company"],
                description=job_data["description"],
                requirements=job_data["requirements"],
                required_skills=job_data["required_skills"],
                experience_level=job_data["experience_level"],
                location=job_data["location"],
                salary_range=job_data.get("salary_range"),
                department=job_data.get("department"),
                job_type=job_data.get("job_type", "full_time"),
                remote_allowed=job_data.get("remote_allowed", False),
                priority=job_data.get("priority", 1),
                status="active",
                embedding_status="pending"
            )
            
            db.add(job)
            db.commit()
            db.refresh(job)
            
            logger.info(f"Created job {job_id}")
            return job_id
            
        except Exception as e:
            logger.error(f"Error creating job: {e}")
            db.rollback()
            raise

    async def process_job_embeddings(self, job_id: str):
        """Process job embeddings in background"""
        try:
            start_time = datetime.utcnow()
            
            # Get job from database
            from app.core.database import SessionLocal
            db = SessionLocal()
            
            try:
                job = db.query(Job).filter(Job.id == job_id).first()
                if not job:
                    raise ValueError(f"Job {job_id} not found")
                
                # Update status
                job.embedding_status = "processing"
                db.commit()
                
                # Prepare job data for embedding
                job_data = {
                    "title": job.title,
                    "company": job.company,
                    "description": job.description,
                    "requirements": job.requirements,
                    "required_skills": job.required_skills,
                    "experience_level": job.experience_level,
                    "location": job.location,
                    "department": job.department
                }
                
                # Store embeddings if service is available
                if self.vector_service:
                    await self.vector_service.store_job_embeddings(job_id, job_data)
                
                # Update status
                job.embedding_status = "completed"
                db.commit()
                
                # Log success
                processing_time = (datetime.utcnow() - start_time).total_seconds()
                log = ProcessingLog(
                    entity_type="job",
                    entity_id=job_id,
                    operation="embedding_generation",
                    status="success",
                    processing_time=processing_time
                )
                db.add(log)
                db.commit()
                
                logger.info(f"Job {job_id} embeddings processed successfully")
                
            except Exception as e:
                # Update status to failed
                if 'job' in locals():
                    job.embedding_status = "failed"
                    db.commit()
                
                # Log error
                processing_time = (datetime.utcnow() - start_time).total_seconds()
                log = ProcessingLog(
                    entity_type="job",
                    entity_id=job_id,
                    operation="embedding_generation",
                    status="failed",
                    error_message=str(e),
                    processing_time=processing_time
                )
                db.add(log)
                db.commit()
                
                logger.error(f"Job {job_id} embedding processing failed: {e}")
                raise
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"Error processing job embeddings: {e}")
            raise

    async def list_jobs_enhanced(
        self, 
        db: Session, 
        skip: int = 0, 
        limit: int = 50, 
        status: Optional[str] = None,
        company: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """List jobs with enhanced filtering"""
        try:
            query = db.query(Job)
            
            if status:
                query = query.filter(Job.status == status)
            if company:
                query = query.filter(Job.company.ilike(f"%{company}%"))
            
            jobs = query.order_by(Job.created_at.desc()).offset(skip).limit(limit).all()
            
            result = []
            for job in jobs:
                result.append({
                    "job_id": str(job.id),
                    "title": job.title,
                    "company": job.company,
                    "location": job.location,
                    "experience_level": job.experience_level,
                    "job_type": job.job_type,
                    "remote_allowed": job.remote_allowed,
                    "status": job.status,
                    "embedding_status": job.embedding_status,
                    "priority": job.priority,
                    "required_skills_count": len(job.required_skills or []),
                    "created_at": job.created_at.isoformat(),
                    "updated_at": job.updated_at.isoformat()
                })
            
            return result
            
        except Exception as e:
            logger.error(f"Error listing jobs: {e}")
            raise

    async def get_job_details(self, job_id: str, db: Session) -> Optional[Dict[str, Any]]:
        """Get detailed job information"""
        try:
            job = db.query(Job).filter(Job.id == job_id).first()
            if not job:
                return None
            
            return {
                "id": str(job.id),
                "title": job.title,
                "company": job.company,
                "description": job.description,
                "requirements": job.requirements,
                "required_skills": job.required_skills,
                "experience_level": job.experience_level,
                "location": job.location,
                "salary_range": job.salary_range,
                "department": job.department,
                "job_type": job.job_type,
                "remote_allowed": job.remote_allowed,
                "priority": job.priority,
                "status": job.status,
                "embedding_status": job.embedding_status,
                "created_at": job.created_at,
                "updated_at": job.updated_at
            }
            
        except Exception as e:
            logger.error(f"Error getting job details: {e}")
            raise

    async def search_jobs_semantic(self, query: str, top_k: int = 20) -> Dict[str, Any]:
        """Perform semantic search on jobs"""
        try:
            # Check cache first
            cache_key = f"search:jobs:{hash(query)}:{top_k}"
            if self.cache_service:
                cached_result = await self.cache_service.get(cache_key)
                if cached_result:
                    return cached_result
            
            # Perform vector search if available
            if self.vector_service:
                results = await self.vector_service.search_similar_jobs(query, top_k)
            else:
                results = {"documents": [[]], "metadatas": [[]], "distances": [[]]}
            
            # Cache results
            if self.cache_service:
                await self.cache_service.set(cache_key, results, ttl=900)  # 15 minutes
            
            return results
            
        except Exception as e:
            logger.error(f"Error in job semantic search: {e}")
            return {"documents": [[]], "metadatas": [[]], "distances": [[]]}

    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on job service"""
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
                "features": ["job_creation", "embedding_processing", "semantic_search"]
            }
            
        except Exception as e:
            logger.error(f"Job service health check failed: {e}")
            return {"status": "unhealthy", "error": str(e)}
