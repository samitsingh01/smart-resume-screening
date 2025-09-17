# backend/app/main.py
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
from datetime import datetime

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
    description="Advanced RAG-based resume screening system with LangGraph workflows",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global services
resume_service: Optional[EnhancedResumeService] = None
job_service: Optional[EnhancedJobService] = None
matching_service: Optional[EnhancedMatchingService] = None
resume_workflow: Optional[ResumeProcessingWorkflow] = None

@app.on_startup
async def startup_event():
    """Initialize services and database on startup"""
    global resume_service, job_service, matching_service, resume_workflow
    
    logger.info("Starting Smart Resume Screening API v2.0...")
    
    try:
        # Create database tables
        create_tables()
        
        # Initialize services
        resume_service = EnhancedResumeService()
        job_service = EnhancedJobService()
        matching_service = EnhancedMatchingService()
        resume_workflow = ResumeProcessingWorkflow()
        
        # Initialize all services
        await asyncio.gather(
            resume_service.initialize(),
            job_service.initialize(),
            matching_service.initialize()
        )
        
        logger.info("All services initialized successfully")
        
    except Exception as e:
        logger.error(f"Startup failed: {e}")
        raise

@app.on_shutdown
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
    
    overall_status = "healthy" if all(s == "healthy" for s in services_status.values()) else "degraded"
    
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
        job_id = await job_service.create_job_enhanced(job.dict(), db)
        
        # Process job embeddings in background
        background_tasks.add_task(job_service.process_job_embeddings, job_id)
        
        return JobResponse(
            job_id=job_id,
            status="created",
            message="Job created successfully and is being processed"
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
        jobs = await job_service.list_jobs_enhanced(
            db, skip=skip, limit=limit, status=status, company=company
        )
        return jobs
    except Exception as e:
        logger.error(f"Error listing jobs: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v2/jobs/{job_id}")
async def get_job_details(job_id: str, db: Session = Depends(get_db)):
    """Get detailed job information"""
    try:
        job = await job_service.get_job_details(job_id, db)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        return job
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
            text_content = await resume_service.extract_text_from_file(tmp_file_path, file.filename)
            
            # Create resume record
            resume_id = await resume_service.create_resume_record(
                filename=file.filename,
                raw_content=text_content,
                file_size=len(content),
                db=db
            )
            
            # Process resume in background using LangGraph workflow
            if background_tasks:
                background_tasks.add_task(
                    resume_workflow.process_resume,
                    resume_id, file.filename, text_content
                )
            
            return ResumeResponse(
                resume_id=resume_id,
                filename=file.filename,
                status="uploaded",
                message="Resume uploaded successfully and is being processed"
            )
            
        finally:
            # Clean up temp file
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
        resumes = await resume_service.list_resumes_enhanced(
            db, skip=skip, limit=limit, status=status
        )
        return resumes
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
        status = await resume_service.get_processing_status(resume_id, db)
        if not status:
            raise HTTPException(status_code=404, detail="Resume not found")
        return ProcessingStatusResponse(**status)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting processing status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Advanced Matching Endpoints
@app.post("/api/v2/match/advanced", response_model=List[MatchResponse])
async def find_advanced_matches(
    job_id: str,
    top_k: int = Query(20, ge=1, le=50),
    min_score: float = Query(0.0, ge=0.0, le=1.0),
    experience_filter: Optional[str] = Query(None),
    skill_filter: Optional[List[str]] = Query(None),
    db: Session = Depends(get_db)
):
    """Find matches using advanced algorithms with filtering"""
    try:
        # Build filters
        filters = {}
        if experience_filter:
            filters["experience_level"] = experience_filter
        
        matches = await matching_service.find_advanced_matches(
            job_id=job_id,
            top_k=top_k,
            filters=filters
        )
        
        # Filter by minimum score
        if min_score > 0:
            matches = [m for m in matches if m["overall_score"] >= min_score * 100]
        
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
        
    except Exception as e:
        logger.error(f"Error in advanced matching: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v2/match/history/{job_id}")
async def get_match_history(
    job_id: str,
    db: Session = Depends(get_db)
):
    """Get historical match results for a job"""
    try:
        matches = db.query(JobResumeMatch).filter(
            JobResumeMatch.job_id == job_id
        ).order_by(JobResumeMatch.overall_score.desc()).all()
        
        if not matches:
            return {"message": "No matches found for this job", "matches": []}
        
        return {
            "job_id": job_id,
            "total_matches": len(matches),
            "matches": [
                {
                    "resume_id": str(match.resume_id),
                    "overall_score": match.overall_score,
                    "skill_match_score": match.skill_match_score,
                    "experience_match_score": match.experience_match_score,
                    "matched_skills": match.matched_skills,
                    "missing_skills": match.missing_skills,
                    "confidence_level": match.confidence_level,
                    "recommendation": match.recommendation,
                    "created_at": match.created_at.isoformat()
                }
                for match in matches
            ]
        }
        
    except Exception as e:
        logger.error(f"Error getting match history: {e}")
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
        resume_status_counts = db.query(
            Resume.processing_status,
            db.func.count(Resume.id)
        ).group_by(Resume.processing_status).all()
        
        job_status_counts = db.query(
            Job.status,
            db.func.count(Job.id)
        ).group_by(Job.status).all()
        
        # Get top skills
        from sqlalchemy import func
        top_skills = db.query(
            func.unnest(Resume.extracted_skills).label('skill'),
            func.count().label('count')
        ).group_by('skill').order_by(func.count().desc()).limit(10).all()
        
        return AnalyticsResponse(
            total_jobs=total_jobs,
            total_resumes=total_resumes,
            total_matches=total_matches,
            resume_status_distribution=dict(resume_status_counts),
            job_status_distribution=dict(job_status_counts),
            top_skills=[{"skill": skill, "count": count} for skill, count in top_skills],
            generated_at=datetime.utcnow().isoformat()
        )
        
    except Exception as e:
        logger.error(f"Error getting analytics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v2/analytics/resume/{resume_id}")
async def get_resume_analytics(
    resume_id: str,
    db: Session = Depends(get_db)
):
    """Get detailed analytics for a specific resume"""
    try:
        resume = db.query(Resume).filter(Resume.id == resume_id).first()
        if not resume:
            raise HTTPException(status_code=404, detail="Resume not found")
        
        # Get match statistics
        matches = db.query(JobResumeMatch).filter(
            JobResumeMatch.resume_id == resume_id
        ).all()
        
        if matches:
            avg_score = sum(m.overall_score for m in matches) / len(matches)
            best_score = max(m.overall_score for m in matches)
            
            # Get skill frequency
            skill_frequency = {}
            for match in matches:
                for skill in match.matched_skills or []:
                    skill_frequency[skill] = skill_frequency.get(skill, 0) + 1
        else:
            avg_score = 0
            best_score = 0
            skill_frequency = {}
        
        return {
            "resume_id": resume_id,
            "filename": resume.filename,
            "total_matches": len(matches),
            "average_score": round(avg_score, 2),
            "best_score": round(best_score, 2),
            "skill_frequency": skill_frequency,
            "processing_status": resume.processing_status,
            "quality_score": resume.quality_score,
            "extracted_skills": resume.extracted_skills,
            "experience_level": resume.experience_level,
            "created_at": resume.created_at.isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting resume analytics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Search and Filter Endpoints
@app.get("/api/v2/search/resumes")
async def search_resumes(
    query: str = Query(..., min_length=3),
    top_k: int = Query(20, ge=1, le=50),
    filters: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """Search resumes using semantic search"""
    try:
        results = await resume_service.search_resumes_semantic(
            query=query,
            top_k=top_k,
            filters=filters
        )
        
        return {
            "query": query,
            "total_results": len(results.get("documents", [{}])[0] if results.get("documents") else []),
            "results": results
        }
        
    except Exception as e:
        logger.error(f"Error searching resumes: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v2/search/jobs")
async def search_jobs(
    query: str = Query(..., min_length=3),
    top_k: int = Query(20, ge=1, le=50),
    db: Session = Depends(get_db)
):
    """Search jobs using semantic search"""
    try:
        results = await job_service.search_jobs_semantic(query, top_k)
        
        return {
            "query": query,
            "total_results": len(results.get("documents", [{}])[0] if results.get("documents") else []),
            "results": results
        }
        
    except Exception as e:
        logger.error(f"Error searching jobs: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Bulk Operations
@app.post("/api/v2/bulk/process-pending")
async def process_pending_items(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Process all pending resumes and jobs"""
    try:
        # Get pending resumes
        pending_resumes = db.query(Resume).filter(
            Resume.processing_status == "pending"
        ).all()
        
        # Get pending jobs
        pending_jobs = db.query(Job).filter(
            Job.embedding_status == "pending"
        ).all()
        
        # Schedule background processing
        for resume in pending_resumes:
            background_tasks.add_task(
                resume_workflow.process_resume,
                str(resume.id), resume.filename, resume.original_content or ""
            )
        
        for job in pending_jobs:
            background_tasks.add_task(
                job_service.process_job_embeddings,
                str(job.id)
            )
        
        return {
            "message": "Bulk processing initiated",
            "pending_resumes": len(pending_resumes),
            "pending_jobs": len(pending_jobs),
            "total_tasks": len(pending_resumes) + len(pending_jobs)
        }
        
    except Exception as e:
        logger.error(f"Error in bulk processing: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Performance and Monitoring
@app.get("/api/v2/performance/metrics")
async def get_performance_metrics(db: Session = Depends(get_db)):
    """Get system performance metrics"""
    try:
        from app.models.database import ProcessingLog
        
        # Get recent processing times
        recent_logs = db.query(ProcessingLog).filter(
            ProcessingLog.created_at >= datetime.utcnow() - timedelta(hours=24)
        ).all()
        
        processing_times = [log.processing_time for log in recent_logs if log.processing_time]
        
        if processing_times:
            avg_processing_time = sum(processing_times) / len(processing_times)
            max_processing_time = max(processing_times)
            min_processing_time = min(processing_times)
        else:
            avg_processing_time = max_processing_time = min_processing_time = 0
        
        return {
            "last_24_hours": {
                "total_operations": len(recent_logs),
                "successful_operations": len([l for l in recent_logs if l.status == "success"]),
                "failed_operations": len([l for l in recent_logs if l.status == "failed"]),
                "average_processing_time": round(avg_processing_time, 2),
                "max_processing_time": round(max_processing_time, 2),
                "min_processing_time": round(min_processing_time, 2)
            },
            "system_status": "healthy",
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting performance metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Error handling
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.error(f"Global exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "type": "internal_error"}
    )

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
        workers=1 if settings.debug else settings.workers,
        log_level=settings.log_level.lower()
    )
