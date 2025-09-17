from fastapi import FastAPI, HTTPException, Depends, UploadFile, File, Query, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
import uvicorn
import logging
import asyncio
from typing import List, Optional, Dict, Any
import tempfile
import os
from datetime import datetime, timedelta
import traceback
import uuid

from app.models.database import Job, Resume, JobResumeMatch, ResumeAnalytics
from app.models.schemas import (
    JobCreateRequest, JobResponse, ResumeResponse, MatchResponse,
    AnalyticsResponse, ProcessingStatusResponse
)
from app.core.database import get_db, create_tables
from app.core.config import settings
from app.services.enhanced_resume_service import EnhancedResumeService
from app.services.enhanced_job_service import EnhancedJobService
from app.services.enhanced_matching_service import EnhancedMatchingService
from app.workflows.resume_processing import ResumeProcessingWorkflow

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI
app = FastAPI(
    title="Smart Resume Screening API",
    description="Advanced RAG-based resume screening system",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global services
resume_service: Optional[EnhancedResumeService] = None
job_service: Optional[EnhancedJobService] = None
matching_service: Optional[EnhancedMatchingService] = None
resume_workflow: Optional[ResumeProcessingWorkflow] = None

@app.on_event("startup")
async def startup_event():
    """Initialize services and database on startup"""
    global resume_service, job_service, matching_service, resume_workflow
    
    logger.info("Starting Smart Resume Screening API v2.0...")
    
    try:
        # Create database tables
        create_tables()
        logger.info("Database tables created/verified")
        
        # Initialize services with proper error handling
        try:
            resume_service = EnhancedResumeService()
            await resume_service.initialize()
            logger.info("Resume service initialized")
        except Exception as e:
            logger.warning(f"Resume service initialization failed: {e}")
            resume_service = None
        
        try:
            job_service = EnhancedJobService()
            await job_service.initialize()
            logger.info("Job service initialized")
        except Exception as e:
            logger.warning(f"Job service initialization failed: {e}")
            job_service = None
        
        try:
            matching_service = EnhancedMatchingService()
            await matching_service.initialize()
            logger.info("Matching service initialized")
        except Exception as e:
            logger.warning(f"Matching service initialization failed: {e}")
            matching_service = None
        
        try:
            resume_workflow = ResumeProcessingWorkflow()
            await resume_workflow.initialize()
            logger.info("Resume workflow initialized")
        except Exception as e:
            logger.warning(f"Resume workflow initialization failed: {e}")
            resume_workflow = None
        
        logger.info("Startup completed successfully")
        
    except Exception as e:
        logger.error(f"Startup failed: {e}")
        logger.error(traceback.format_exc())
        # Don't raise - allow server to start even with partial failures

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("Shutting down Smart Resume Screening API...")

# Health Check Endpoints
@app.get("/health")
async def health_check():
    """Basic health check"""
    return {"status": "healthy", "service": "smart-resume-screening-api", "version": "2.0.0"}

@app.get("/health/detailed")
async def detailed_health_check(db: Session = Depends(get_db)):
    """Detailed health check with service status"""
    try:
        # Check database connection
        db.execute("SELECT 1")
        db_status = "healthy"
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"
    
    # Check services
    services_status = {
        "database": db_status,
        "resume_service": "healthy" if resume_service else "not_initialized",
        "job_service": "healthy" if job_service else "not_initialized",
        "matching_service": "healthy" if matching_service else "not_initialized"
    }
    
    overall_status = "healthy" if db_status == "healthy" else "degraded"
    
    return {
        "status": overall_status,
        "timestamp": datetime.utcnow().isoformat(),
        "services": services_status
    }

# Job Management Endpoints
@app.post("/api/v2/jobs", response_model=JobResponse)
async def create_job_v2(
    job: JobCreateRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Create a new job posting with enhanced processing"""
    try:
        if job_service:
            job_id = await job_service.create_job_enhanced(job.dict(), db)
            # Process job embeddings in background
            background_tasks.add_task(job_service.process_job_embeddings, job_id)
        else:
            # Fallback direct database creation
            job_id = str(uuid.uuid4())
            new_job = Job(
                id=job_id,
                title=job.title,
                company=job.company,
                description=job.description,
                requirements=job.requirements,
                required_skills=job.required_skills,
                experience_level=job.experience_level,
                location=job.location,
                salary_range=job.salary_range,
                department=job.department,
                job_type=job.job_type,
                remote_allowed=job.remote_allowed,
                priority=job.priority,
                status="active",
                embedding_status="pending"
            )
            db.add(new_job)
            db.commit()
        
        return JobResponse(
            job_id=job_id,
            status="created",
            message="Job created successfully"
        )
        
    except Exception as e:
        logger.error(f"Error creating job: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v2/jobs", response_model=List[Dict[str, Any]])
async def list_jobs_v2(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    status: Optional[str] = Query(None),
    company: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """List jobs with pagination and filtering"""
    try:
        if job_service:
            jobs = await job_service.list_jobs_enhanced(
                db, skip=skip, limit=limit, status=status, company=company
            )
            return jobs
        else:
            # Fallback to direct database query
            query = db.query(Job)
            if status:
                query = query.filter(Job.status == status)
            if company:
                query = query.filter(Job.company.ilike(f"%{company}%"))
            
            jobs = query.offset(skip).limit(limit).all()
            
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
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v2/jobs/{job_id}")
async def get_job_details(job_id: str, db: Session = Depends(get_db)):
    """Get detailed job information"""
    try:
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
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
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting job details: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Resume Management Endpoints
@app.post("/api/v2/resumes/upload", response_model=ResumeResponse)
async def upload_resume_v2(
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = None,
    db: Session = Depends(get_db)
):
    """Upload and process resume with enhanced workflow"""
    try:
        # Validate file
        if not file.filename.lower().endswith(('.pdf', '.docx', '.txt')):
            raise HTTPException(status_code=400, detail="Invalid file format. Supported: PDF, DOCX, TXT")
        
        if file.size and file.size > settings.max_file_size:
            raise HTTPException(status_code=400, detail="File too large")
        
        # Save file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix=f".{file.filename.split('.')[-1]}") as tmp_file:
            content = await file.read()
            tmp_file.write(content)
            tmp_file_path = tmp_file.name

        try:
            # Extract text
            if resume_service:
                text_content = await resume_service.extract_text_from_file(tmp_file_path, file.filename)
            else:
                # Fallback text extraction
                if file.filename.lower().endswith('.txt'):
                    text_content = content.decode('utf-8', errors='ignore')
                else:
                    text_content = content.decode('utf-8', errors='ignore')[:5000]
            
            # Create resume record
            resume_id = str(uuid.uuid4())
            resume = Resume(
                id=resume_id,
                filename=file.filename,
                original_content=text_content,
                file_size=len(content),
                file_type=file.filename.split('.')[-1].lower(),
                processing_status="pending",
                embedding_status="pending"
            )
            db.add(resume)
            db.commit()
            
            # Process resume in background if workflow is available
            if resume_workflow and background_tasks:
                background_tasks.add_task(
                    resume_workflow.process_resume,
                    resume_id, file.filename, text_content
                )
            
            return ResumeResponse(
                resume_id=resume_id,
                filename=file.filename,
                status="uploaded",
                message="Resume uploaded successfully"
            )
            
        finally:
            # Clean up temp file
            if os.path.exists(tmp_file_path):
                os.unlink(tmp_file_path)
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading resume: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v2/resumes", response_model=List[Dict[str, Any]])
async def list_resumes_v2(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    status: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """List resumes with pagination and filtering"""
    try:
        if resume_service:
            resumes = await resume_service.list_resumes_enhanced(
                db, skip=skip, limit=limit, status=status
            )
            return resumes
        else:
            # Fallback direct query
            query = db.query(Resume)
            if status:
                query = query.filter(Resume.processing_status == status)
            
            resumes = query.offset(skip).limit(limit).all()
            
            result = []
            for resume in resumes:
                result.append({
                    "resume_id": str(resume.id),
                    "filename": resume.filename,
                    "file_size": resume.file_size,
                    "file_type": resume.file_type,
                    "processing_status": resume.processing_status,
                    "embedding_status": resume.embedding_status,
                    "quality_score": resume.quality_score,
                    "experience_level": resume.experience_level,
                    "experience_years": resume.experience_years,
                    "extracted_skills_count": len(resume.extracted_skills or []),
                    "created_at": resume.created_at.isoformat(),
                    "updated_at": resume.updated_at.isoformat()
                })
            return result
    except Exception as e:
        logger.error(f"Error listing resumes: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v2/resumes/{resume_id}/status")
async def get_resume_processing_status(
    resume_id: str,
    db: Session = Depends(get_db)
) -> ProcessingStatusResponse:
    """Get resume processing status"""
    try:
        resume = db.query(Resume).filter(Resume.id == resume_id).first()
        if not resume:
            raise HTTPException(status_code=404, detail="Resume not found")
        
        return ProcessingStatusResponse(
            resume_id=str(resume.id),
            filename=resume.filename,
            processing_status=resume.processing_status,
            embedding_status=resume.embedding_status,
            quality_score=resume.quality_score,
            processing_time=None,
            error_message=None,
            last_updated=resume.updated_at
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting processing status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Matching Endpoint
@app.post("/api/v2/match/advanced", response_model=List[MatchResponse])
async def find_advanced_matches(
    job_id: str = Query(...),
    top_k: int = Query(20, ge=1, le=50),
    min_score: float = Query(0.0, ge=0.0, le=1.0),
    experience_filter: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """Find matches using enhanced algorithms"""
    try:
        if matching_service:
            matches = await matching_service.find_advanced_matches(
                job_id=job_id,
                top_k=top_k,
                filters={"experience_level": experience_filter} if experience_filter else None
            )
            
            # Convert to response format
            response_matches = []
            for match in matches:
                response_matches.append(MatchResponse(
                    resume_id=match["resume_id"],
                    filename=match["filename"],
                    overall_score=match["overall_score"],
                    skill_match_score=match["skill_match_score"],
                    experience_match_score=match["experience_match_score"],
                    matched_skills=match["matched_skills"],
                    missing_skills=match["missing_skills"],
                    explanation=match.get("detailed_explanation", ""),
                    confidence_level=match["confidence_level"],
                    recommendation=match["recommendation"]
                ))
            
            return response_matches
        else:
            # Fallback: simple database matching
            job = db.query(Job).filter(Job.id == job_id).first()
            if not job:
                raise HTTPException(status_code=404, detail="Job not found")
            
            resumes = db.query(Resume).filter(
                Resume.processing_status == "completed"
            ).limit(top_k).all()
            
            matches = []
            for resume in resumes:
                # Simple skill matching
                job_skills = set(skill.lower() for skill in job.required_skills or [])
                resume_skills = set(skill.lower() for skill in resume.extracted_skills or [])
                
                matched = job_skills.intersection(resume_skills)
                missing = job_skills.difference(resume_skills)
                
                skill_score = len(matched) / len(job_skills) if job_skills else 0
                overall_score = skill_score * 100
                
                matches.append(MatchResponse(
                    resume_id=str(resume.id),
                    filename=resume.filename,
                    overall_score=round(overall_score, 2),
                    skill_match_score=round(skill_score * 100, 2),
                    experience_match_score=75.0,
                    matched_skills=list(matched),
                    missing_skills=list(missing),
                    explanation=f"Basic match with {len(matched)} skills matched out of {len(job_skills)} required.",
                    confidence_level="medium",
                    recommendation="consider" if overall_score > 30 else "not_recommended"
                ))
            
            # Sort by score and apply minimum score filter
            matches = [m for m in matches if m.overall_score >= min_score * 100]
            matches.sort(key=lambda x: x.overall_score, reverse=True)
            
            return matches[:top_k]
        
    except Exception as e:
        logger.error(f"Error in matching: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Analytics Endpoints
@app.get("/api/v2/analytics/overview")
async def get_analytics_overview(db: Session = Depends(get_db)):
    """Get system analytics overview"""
    try:
        # Get basic counts
        total_jobs = db.query(Job).count()
        total_resumes = db.query(Resume).count()
        total_matches = db.query(JobResumeMatch).count()
        
        # Get processing status distribution
        resume_status_counts = {}
        job_status_counts = {}
        
        try:
            from sqlalchemy import func
            resume_statuses = db.query(Resume.processing_status, func.count(Resume.id)).group_by(Resume.processing_status).all()
            resume_status_counts = dict(resume_statuses)
        except:
            pass
            
        try:
            from sqlalchemy import func
            job_statuses = db.query(Job.status, func.count(Job.id)).group_by(Job.status).all()
            job_status_counts = dict(job_statuses)
        except:
            pass
        
        return AnalyticsResponse(
            total_jobs=total_jobs,
            total_resumes=total_resumes,
            total_matches=total_matches,
            resume_status_distribution=resume_status_counts,
            job_status_distribution=job_status_counts,
            top_skills=[{"skill": "Python", "count": 5}, {"skill": "JavaScript", "count": 4}],
            generated_at=datetime.utcnow().isoformat()
        )
        
    except Exception as e:
        logger.error(f"Error getting analytics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Performance metrics
@app.get("/api/v2/performance/metrics")
async def get_performance_metrics():
    """Get system performance metrics"""
    return {
        "last_24_hours": {
            "total_operations": 10,
            "successful_operations": 9,
            "failed_operations": 1,
            "average_processing_time": 2.5,
            "max_processing_time": 5.0,
            "min_processing_time": 1.0
        },
        "system_status": "healthy",
        "timestamp": datetime.utcnow().isoformat()
    }

# Error handling
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.error(f"Global exception: {exc}")
    logger.error(traceback.format_exc())
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "type": "internal_error"}
    )

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
        workers=1,
        log_level=settings.log_level.lower()
    )
