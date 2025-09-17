from pydantic import BaseModel, validator
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum

class ExperienceLevel(str, Enum):
    ENTRY = "entry"
    MID = "mid"
    SENIOR = "senior"
    LEAD = "lead"

class JobType(str, Enum):
    FULL_TIME = "full_time"
    PART_TIME = "part_time"
    CONTRACT = "contract"
    REMOTE = "remote"

class ProcessingStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class ConfidenceLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

class Recommendation(str, Enum):
    STRONGLY_RECOMMENDED = "strongly_recommended"
    RECOMMENDED = "recommended"
    CONSIDER = "consider"
    NOT_RECOMMENDED = "not_recommended"

# Job Models
class JobCreateRequest(BaseModel):
    title: str
    company: str
    description: str
    requirements: List[str]
    required_skills: List[str]
    experience_level: ExperienceLevel
    location: str
    salary_range: Optional[str] = None
    department: Optional[str] = None
    job_type: JobType = JobType.FULL_TIME
    remote_allowed: bool = False
    priority: int = 1
    
    @validator('title', 'company', 'description')
    def validate_required_fields(cls, v):
        if not v or not v.strip():
            raise ValueError('Field cannot be empty')
        return v.strip()
    
    @validator('requirements', 'required_skills')
    def validate_lists(cls, v):
        if not v:
            raise ValueError('At least one item required')
        return [item.strip() for item in v if item.strip()]

class JobResponse(BaseModel):
    job_id: str
    status: str
    message: str

class JobDetailResponse(BaseModel):
    id: str
    title: str
    company: str
    description: str
    requirements: List[str]
    required_skills: List[str]
    experience_level: str
    location: str
    salary_range: Optional[str]
    department: Optional[str]
    job_type: str
    remote_allowed: bool
    priority: int
    status: str
    embedding_status: str
    created_at: datetime
    updated_at: datetime

# Resume Models
class ResumeResponse(BaseModel):
    resume_id: str
    filename: str
    status: str
    message: str

class ResumeDetailResponse(BaseModel):
    id: str
    filename: str
    extracted_skills: Optional[List[str]]
    experience_years: Optional[int]
    experience_level: Optional[str]
    education: Optional[Dict[str, Any]]
    certifications: Optional[List[str]]
    contact_info: Optional[Dict[str, Any]]
    file_size: Optional[int]
    file_type: Optional[str]
    processing_status: str
    embedding_status: str
    quality_score: Optional[float]
    created_at: datetime
    updated_at: datetime

class ProcessingStatusResponse(BaseModel):
    resume_id: str
    filename: str
    processing_status: ProcessingStatus
    embedding_status: ProcessingStatus
    quality_score: Optional[float]
    processing_time: Optional[float]
    error_message: Optional[str]
    last_updated: datetime

# Matching Models
class MatchResponse(BaseModel):
    resume_id: str
    filename: str
    overall_score: float
    skill_match_score: float
    experience_match_score: float
    matched_skills: List[str]
    missing_skills: List[str]
    explanation: str
    confidence_level: ConfidenceLevel
    recommendation: Recommendation

class MatchRequest(BaseModel):
    job_id: str
    top_k: int = 20
    min_score: float = 0.0
    filters: Optional[Dict[str, Any]] = None

# Analytics Models
class AnalyticsResponse(BaseModel):
    total_jobs: int
    total_resumes: int
    total_matches: int
    resume_status_distribution: Dict[str, int]
    job_status_distribution: Dict[str, int]
    top_skills: List[Dict[str, Any]]
    generated_at: str

class SkillAnalytics(BaseModel):
    skill: str
    frequency: int
    avg_match_score: float
    jobs_requiring: int

# Search Models
class SearchRequest(BaseModel):
    query: str
    top_k: int = 20
    filters: Optional[Dict[str, Any]] = None

class SearchResponse(BaseModel):
    query: str
    total_results: int
    results: List[Dict[str, Any]]
    execution_time: float

# Bulk Operations
class BulkProcessingResponse(BaseModel):
    message: str
    pending_resumes: int
    pending_jobs: int
    total_tasks: int
    estimated_completion_time: Optional[str] = None

# Performance Models
class PerformanceMetrics(BaseModel):
    last_24_hours: Dict[str, Any]
    system_status: str
    timestamp: str
