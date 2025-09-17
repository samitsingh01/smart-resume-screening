import logging
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime
import aiofiles
import tempfile
import os
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from app.models.database import Resume, ProcessingLog
from app.services.vector_service import VectorService
from app.services.cache_service import CacheService
from app.core.config import settings

logger = logging.getLogger(__name__)

class EnhancedResumeService:
    def __init__(self):
        self.vector_service = VectorService()
        self.cache_service = CacheService()

    async def initialize(self):
        """Initialize enhanced resume service"""
        try:
            await self.vector_service.initialize()
            await self.cache_service.initialize()
            logger.info("Enhanced resume service initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize enhanced resume service: {e}")
            # Don't raise - allow partial functionality

    async def extract_text_from_file(self, file_path: str, filename: str) -> str:
        """Extract text from various file formats"""
        try:
            file_ext = filename.lower().split('.')[-1]
            
            if file_ext == 'pdf':
                return await self._extract_from_pdf(file_path)
            elif file_ext == 'docx':
                return await self._extract_from_docx(file_path)
            elif file_ext == 'txt':
                return await self._extract_from_txt(file_path)
            else:
                raise ValueError(f"Unsupported file format: {file_ext}")
                
        except Exception as e:
            logger.error(f"Error extracting text from {filename}: {e}")
            raise

    async def _extract_from_pdf(self, file_path: str) -> str:
        """Extract text from PDF files"""
        try:
            import PyPDF2
            text = ""
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                for page in pdf_reader.pages:
                    text += page.extract_text() + "\n"
            
            # Clean extracted text
            text = text.replace('\n\n', '\n').strip()
            return text
            
        except Exception as e:
            logger.error(f"PDF extraction failed: {e}")
            # Fallback: try to read as text
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    return f.read()
            except:
                raise Exception(f"Could not extract text from PDF: {e}")

    async def _extract_from_docx(self, file_path: str) -> str:
        """Extract text from DOCX files"""
        try:
            import docx2txt
            text = docx2txt.process(file_path)
            return text.strip() if text else ""
        except Exception as e:
            logger.error(f"DOCX extraction failed: {e}")
            # Fallback: try alternative method
            try:
                from docx import Document
                doc = Document(file_path)
                text = []
                for paragraph in doc.paragraphs:
                    text.append(paragraph.text)
                return '\n'.join(text)
            except:
                raise Exception(f"Could not extract text from DOCX: {e}")

    async def _extract_from_txt(self, file_path: str) -> str:
        """Extract text from TXT files"""
        try:
            # Try different encodings
            encodings = ['utf-8', 'utf-16', 'latin-1', 'ascii']
            
            for encoding in encodings:
                try:
                    async with aiofiles.open(file_path, 'r', encoding=encoding) as file:
                        content = await file.read()
                        return content
                except UnicodeDecodeError:
                    continue
            
            # If all encodings fail, read as bytes and decode with errors='ignore'
            with open(file_path, 'rb') as file:
                content = file.read()
                return content.decode('utf-8', errors='ignore')
                
        except Exception as e:
            logger.error(f"TXT extraction failed: {e}")
            raise

    async def create_resume_record(self, filename: str, raw_content: str, file_size: int, db: Session) -> str:
        """Create initial resume record in database"""
        try:
            resume_id = str(uuid.uuid4())
            
            resume = Resume(
                id=resume_id,
                filename=filename,
                original_content=raw_content,
                file_size=file_size,
                file_type=filename.split('.')[-1].lower(),
                processing_status="pending",
                embedding_status="pending"
            )
            
            db.add(resume)
            db.commit()
            db.refresh(resume)
            
            logger.info(f"Created resume record {resume_id}")
            return resume_id
            
        except Exception as e:
            logger.error(f"Error creating resume record: {e}")
            db.rollback()
            raise

    async def list_resumes_enhanced(
        self, 
        db: Session, 
        skip: int = 0, 
        limit: int = 50, 
        status: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """List resumes with enhanced filtering"""
        try:
            query = db.query(Resume)
            
            if status:
                query = query.filter(Resume.processing_status == status)
            
            resumes = query.order_by(Resume.created_at.desc()).offset(skip).limit(limit).all()
            
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
            raise

    async def get_processing_status(self, resume_id: str, db: Session) -> Optional[Dict[str, Any]]:
        """Get detailed processing status for a resume"""
        try:
            resume = db.query(Resume).filter(Resume.id == resume_id).first()
            if not resume:
                return None
            
            # Get latest processing log
            latest_log = db.query(ProcessingLog).filter(
                and_(
                    ProcessingLog.entity_type == "resume",
                    ProcessingLog.entity_id == resume_id
                )
            ).order_by(ProcessingLog.created_at.desc()).first()
            
            return {
                "resume_id": str(resume.id),
                "filename": resume.filename,
                "processing_status": resume.processing_status,
                "embedding_status": resume.embedding_status,
                "quality_score": resume.quality_score,
                "processing_time": latest_log.processing_time if latest_log else None,
                "error_message": latest_log.error_message if latest_log else None,
                "last_updated": resume.updated_at
            }
            
        except Exception as e:
            logger.error(f"Error getting processing status: {e}")
            raise

    async def search_resumes_semantic(
        self, 
        query: str, 
        top_k: int = 20, 
        filters: Optional[str] = None
    ) -> Dict[str, Any]:
        """Perform semantic search on resumes"""
        try:
            # Check cache first if available
            cache_key = f"search:resumes:{hash(query)}:{top_k}:{hash(str(filters))}"
            if self.cache_service:
                cached_result = await self.cache_service.get(cache_key)
                if cached_result:
                    return cached_result
            
            # Parse filters if provided
            filter_dict = {}
            if filters:
                try:
                    import json
                    filter_dict = json.loads(filters)
                except json.JSONDecodeError:
                    logger.warning(f"Invalid filter format: {filters}")
            
            # Perform vector search if available
            if self.vector_service:
                results = await self.vector_service.search_similar_resumes(
                    query=query,
                    top_k=top_k,
                    filters=filter_dict
                )
            else:
                # Fallback to basic text search
                results = {"documents": [[]], "metadatas": [[]], "distances": [[]]}
            
            # Cache results if cache is available
            if self.cache_service:
                await self.cache_service.set(cache_key, results, ttl=900)  # 15 minutes
            
            return results
            
        except Exception as e:
            logger.error(f"Error in semantic search: {e}")
            return {"documents": [[]], "metadatas": [[]], "distances": [[]]}

    async def get_resume_details(self, resume_id: str, db: Session) -> Optional[Dict[str, Any]]:
        """Get detailed resume information"""
        try:
            resume = db.query(Resume).filter(Resume.id == resume_id).first()
            if not resume:
                return None
            
            return {
                "id": str(resume.id),
                "filename": resume.filename,
                "extracted_skills": resume.extracted_skills,
                "experience_years": resume.experience_years,
                "experience_level": resume.experience_level,
                "education": resume.education,
                "certifications": resume.certifications,
                "contact_info": resume.contact_info,
                "file_size": resume.file_size,
                "file_type": resume.file_type,
                "processing_status": resume.processing_status,
                "embedding_status": resume.embedding_status,
                "quality_score": resume.quality_score,
                "created_at": resume.created_at,
                "updated_at": resume.updated_at
            }
            
        except Exception as e:
            logger.error(f"Error getting resume details: {e}")
            raise

    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on resume service"""
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
                "supported_formats": ["pdf", "docx", "txt"],
                "max_file_size": settings.max_file_size
            }
            
        except Exception as e:
            logger.error(f"Resume service health check failed: {e}")
            return {"status": "unhealthy", "error": str(e)}

