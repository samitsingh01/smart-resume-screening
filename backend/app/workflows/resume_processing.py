# backend/app/workflows/resume_processing.py
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict, Annotated
from typing import List, Dict, Any
import logging
from datetime import datetime

from app.services.nlp_service import NLPService
from app.services.vector_service import VectorService
from app.core.database import get_db
from app.models.database import Resume, ProcessingLog

logger = logging.getLogger(__name__)

class ResumeProcessingState(TypedDict):
    resume_id: str
    filename: str
    raw_content: str
    processed_content: str
    extracted_data: Dict[str, Any]
    skills: List[str]
    experience_data: Dict[str, Any]
    quality_metrics: Dict[str, float]
    embeddings: List[float]
    status: str
    errors: List[str]
    processing_time: float

class ResumeProcessingWorkflow:
    def __init__(self):
        self.nlp_service = NLPService()
        self.vector_service = VectorService()
        self.graph = self._build_graph()

    def _build_graph(self) -> StateGraph:
        """Build the resume processing workflow graph"""
        workflow = StateGraph(ResumeProcessingState)
        
        # Add nodes
        workflow.add_node("extract_text", self._extract_text)
        workflow.add_node("clean_content", self._clean_content)
        workflow.add_node("extract_skills", self._extract_skills)
        workflow.add_node("extract_experience", self._extract_experience)
        workflow.add_node("extract_education", self._extract_education)
        workflow.add_node("calculate_quality", self._calculate_quality)
        workflow.add_node("generate_embeddings", self._generate_embeddings)
        workflow.add_node("save_to_database", self._save_to_database)
        workflow.add_node("handle_error", self._handle_error)
        
        # Define edges
        workflow.add_edge(START, "extract_text")
        workflow.add_edge("extract_text", "clean_content")
        workflow.add_edge("clean_content", "extract_skills")
        workflow.add_edge("extract_skills", "extract_experience")
        workflow.add_edge("extract_experience", "extract_education")
        workflow.add_edge("extract_education", "calculate_quality")
        workflow.add_edge("calculate_quality", "generate_embeddings")
        workflow.add_edge("generate_embeddings", "save_to_database")
        workflow.add_edge("save_to_database", END)
        workflow.add_edge("handle_error", END)
        
        return workflow.compile()

    async def process_resume(self, resume_id: str, filename: str, raw_content: str) -> Dict[str, Any]:
        """Process a resume through the workflow"""
        start_time = datetime.utcnow()
        
        initial_state = ResumeProcessingState(
            resume_id=resume_id,
            filename=filename,
            raw_content=raw_content,
            processed_content="",
            extracted_data={},
            skills=[],
            experience_data={},
            quality_metrics={},
            embeddings=[],
            status="processing",
            errors=[],
            processing_time=0.0
        )
        
        try:
            result = await self.graph.ainvoke(initial_state)
            result["processing_time"] = (datetime.utcnow() - start_time).total_seconds()
            return result
        except Exception as e:
            logger.error(f"Error processing resume {resume_id}: {e}")
            return await self._handle_error({**initial_state, "errors": [str(e)]})

    async def _extract_text(self, state: ResumeProcessingState) -> ResumeProcessingState:
        """Extract and clean text from raw content"""
        try:
            # Basic text cleaning
            content = state["raw_content"]
            # Remove excessive whitespace
            content = " ".join(content.split())
            # Remove special characters but keep important punctuation
            import re
            content = re.sub(r'[^\w\s\-\.\@\(\)]', ' ', content)
            
            state["processed_content"] = content
            logger.info(f"Text extracted for resume {state['resume_id']}")
            return state
        except Exception as e:
            state["errors"].append(f"Text extraction failed: {e}")
            return state

    async def _clean_content(self, state: ResumeProcessingState) -> ResumeProcessingState:
        """Clean and normalize content"""
        try:
            content = await self.nlp_service.clean_text(state["processed_content"])
            state["processed_content"] = content
            return state
        except Exception as e:
            state["errors"].append(f"Content cleaning failed: {e}")
            return state

    async def _extract_skills(self, state: ResumeProcessingState) -> ResumeProcessingState:
        """Extract skills from resume content"""
        try:
            skills = await self.nlp_service.extract_skills(state["processed_content"])
            state["skills"] = skills
            state["extracted_data"]["skills"] = skills
            return state
        except Exception as e:
            state["errors"].append(f"Skill extraction failed: {e}")
            return state

    async def _extract_experience(self, state: ResumeProcessingState) -> ResumeProcessingState:
        """Extract experience information"""
        try:
            experience_data = await self.nlp_service.extract_experience(state["processed_content"])
            state["experience_data"] = experience_data
            state["extracted_data"]["experience"] = experience_data
            return state
        except Exception as e:
            state["errors"].append(f"Experience extraction failed: {e}")
            return state

    async def _extract_education(self, state: ResumeProcessingState) -> ResumeProcessingState:
        """Extract education information"""
        try:
            education_data = await self.nlp_service.extract_education(state["processed_content"])
            state["extracted_data"]["education"] = education_data
            return state
        except Exception as e:
            state["errors"].append(f"Education extraction failed: {e}")
            return state

    async def _calculate_quality(self, state: ResumeProcessingState) -> ResumeProcessingState:
        """Calculate resume quality metrics"""
        try:
            quality_metrics = await self.nlp_service.calculate_quality_score(
                state["processed_content"],
                state["skills"],
                state["experience_data"]
            )
            state["quality_metrics"] = quality_metrics
            return state
        except Exception as e:
            state["errors"].append(f"Quality calculation failed: {e}")
            return state

    async def _generate_embeddings(self, state: ResumeProcessingState) -> ResumeProcessingState:
        """Generate embeddings for the resume"""
        try:
            embeddings = await self.vector_service.generate_embeddings(state["processed_content"])
            state["embeddings"] = embeddings
            return state
        except Exception as e:
            state["errors"].append(f"Embedding generation failed: {e}")
            return state

    async def _save_to_database(self, state: ResumeProcessingState) -> ResumeProcessingState:
        """Save processed data to database"""
        try:
            db = next(get_db())
            
            # Update resume record
            resume = db.query(Resume).filter(Resume.id == state["resume_id"]).first()
            if resume:
                resume.processed_content = state["processed_content"]
                resume.extracted_skills = state["skills"]
                resume.experience_level = state["experience_data"].get("level", "")
                resume.experience_years = state["experience_data"].get("years", 0)
                resume.education = state["extracted_data"].get("education", {})
                resume.quality_score = state["quality_metrics"].get("overall_score", 0.0)
                resume.processing_status = "completed"
                resume.embedding_status = "completed"
                
                db.commit()
            
            # Save processing log
            log = ProcessingLog(
                entity_type="resume",
                entity_id=state["resume_id"],
                operation="full_processing",
                status="success" if not state["errors"] else "partial_success",
                details=state["extracted_data"],
                processing_time=state["processing_time"]
            )
            db.add(log)
            db.commit()
            
            state["status"] = "completed"
            return state
        except Exception as e:
            state["errors"].append(f"Database save failed: {e}")
            return state
        finally:
            db.close()

    async def _handle_error(self, state: ResumeProcessingState) -> ResumeProcessingState:
        """Handle processing errors"""
        try:
            db = next(get_db())
            
            # Update resume status
            resume = db.query(Resume).filter(Resume.id == state["resume_id"]).first()
            if resume:
                resume.processing_status = "failed"
                db.commit()
            
            # Log error
            log = ProcessingLog(
                entity_type="resume",
                entity_id=state["resume_id"],
                operation="full_processing",
                status="failed",
                error_message="; ".join(state["errors"]),
                processing_time=state["processing_time"]
            )
            db.add(log)
            db.commit()
            
            state["status"] = "failed"
            return state
        except Exception as e:
            logger.error(f"Error handling failed: {e}")
            return state
        finally:
            db.close()

