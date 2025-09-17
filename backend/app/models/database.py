# backend/app/models/database.py
from sqlalchemy import create_engine, Column, String, Text, DateTime, Float, Integer, JSON, Boolean, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from datetime import datetime
import uuid

Base = declarative_base()

class Job(Base):
    __tablename__ = "jobs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(255), nullable=False, index=True)
    company = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=False)
    requirements = Column(ARRAY(Text), nullable=False)
    required_skills = Column(ARRAY(String), nullable=False)
    experience_level = Column(String(50), nullable=False)
    location = Column(String(255), nullable=False)
    salary_range = Column(String(100))
    department = Column(String(100))
    job_type = Column(String(50), default="Full-time")
    remote_allowed = Column(Boolean, default=False)
    priority = Column(Integer, default=1)
    status = Column(String(50), default="active")
    embedding_status = Column(String(50), default="pending")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    matches = relationship("JobResumeMatch", back_populates="job")

class Resume(Base):
    __tablename__ = "resumes"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    filename = Column(String(255), nullable=False)
    original_content = Column(Text)
    processed_content = Column(Text)
    extracted_skills = Column(ARRAY(String))
    experience_years = Column(Integer)
    experience_level = Column(String(50))
    education = Column(JSON)
    certifications = Column(ARRAY(String))
    contact_info = Column(JSON)
    file_size = Column(Integer)
    file_type = Column(String(50))
    processing_status = Column(String(50), default="pending")
    embedding_status = Column(String(50), default="pending")
    quality_score = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    matches = relationship("JobResumeMatch", back_populates="resume")
    analytics = relationship("ResumeAnalytics", back_populates="resume")

class JobResumeMatch(Base):
    __tablename__ = "job_resume_matches"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id = Column(UUID(as_uuid=True), ForeignKey("jobs.id"), nullable=False)
    resume_id = Column(UUID(as_uuid=True), ForeignKey("resumes.id"), nullable=False)
    overall_score = Column(Float, nullable=False)
    skill_match_score = Column(Float)
    experience_match_score = Column(Float)
    education_match_score = Column(Float)
    matched_skills = Column(ARRAY(String))
    missing_skills = Column(ARRAY(String))
    explanation = Column(Text)
    confidence_level = Column(String(20))
    recommendation = Column(String(50))
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    job = relationship("Job", back_populates="matches")
    resume = relationship("Resume", back_populates="matches")

class ResumeAnalytics(Base):
    __tablename__ = "resume_analytics"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    resume_id = Column(UUID(as_uuid=True), ForeignKey("resumes.id"), nullable=False)
    total_matches = Column(Integer, default=0)
    avg_match_score = Column(Float)
    best_match_score = Column(Float)
    skill_frequency = Column(JSON)
    match_trends = Column(JSON)
    last_updated = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    resume = relationship("Resume", back_populates="analytics")

class ProcessingLog(Base):
    __tablename__ = "processing_logs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    entity_type = Column(String(50), nullable=False)  # 'job' or 'resume'
    entity_id = Column(UUID(as_uuid=True), nullable=False)
    operation = Column(String(50), nullable=False)
    status = Column(String(50), nullable=False)
    details = Column(JSON)
    error_message = Column(Text)
    processing_time = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)

