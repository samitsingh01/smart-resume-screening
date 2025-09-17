# backend/app/services/nlp_service.py
import re
import logging
from typing import List, Dict, Any
from langchain_aws import BedrockLLM
from langchain.prompts import PromptTemplate
import spacy
from app.core.config import settings

logger = logging.getLogger(__name__)

class NLPService:
    def __init__(self):
        self.llm = BedrockLLM(
            model_id="anthropic.claude-3-haiku-20240307-v1:0",
            region_name=settings.aws_region,
            model_kwargs={"max_tokens": 2000, "temperature": 0.1}
        )
        
        # Load spaCy model for NER
        try:
            self.nlp = spacy.load("en_core_web_sm")
        except OSError:
            logger.warning("spaCy model not found, using basic text processing")
            self.nlp = None

    async def clean_text(self, text: str) -> str:
        """Clean and normalize text"""
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text)
        # Remove special characters but keep important ones
        text = re.sub(r'[^\w\s\-\.\@\(\)\+]', ' ', text)
        # Normalize case for better processing
        return text.strip()

    async def extract_skills(self, text: str) -> List[str]:
        """Extract skills from resume text using LLM"""
        prompt = PromptTemplate(
            input_variables=["resume_text"],
            template="""
            Extract technical and professional skills from this resume text. 
            Focus on:
            - Programming languages
            - Frameworks and libraries
            - Tools and technologies
            - Certifications
            - Professional skills
            
            Resume text: {resume_text}
            
            Return only a comma-separated list of skills, no explanations.
            """
        )
        
        try:
            response = await self.llm.ainvoke(prompt.format(resume_text=text[:3000]))
            skills = [skill.strip() for skill in response.split(',') if skill.strip()]
            return skills[:20]  # Limit to top 20 skills
        except Exception as e:
            logger.error(f"Skill extraction failed: {e}")
            return self._extract_skills_fallback(text)

    def _extract_skills_fallback(self, text: str) -> List[str]:
        """Fallback skill extraction using pattern matching"""
        common_skills = [
            'Python', 'Java', 'JavaScript', 'React', 'Node.js', 'SQL', 'AWS', 'Docker',
            'Kubernetes', 'Git', 'HTML', 'CSS', 'MongoDB', 'PostgreSQL', 'Linux',
            'Machine Learning', 'Deep Learning', 'TensorFlow', 'PyTorch', 'Pandas'
        ]
        
        found_skills = []
        text_lower = text.lower()
        
        for skill in common_skills:
            if skill.lower() in text_lower:
                found_skills.append(skill)
        
        return found_skills

    async def extract_experience(self, text: str) -> Dict[str, Any]:
        """Extract experience information"""
        prompt = PromptTemplate(
            input_variables=["resume_text"],
            template="""
            Analyze this resume and extract experience information:
            
            {resume_text}
            
            Provide a JSON response with:
            {{
                "years": <total years of experience as integer>,
                "level": "<entry/mid/senior/lead>",
                "positions": [list of job titles],
                "companies": [list of companies]
            }}
            
            Return only valid JSON, no explanations.
            """
        )
        
        try:
            response = await self.llm.ainvoke(prompt.format(resume_text=text[:3000]))
            # Parse JSON response
            import json
            return json.loads(response.strip())
        except Exception as e:
            logger.error(f"Experience extraction failed: {e}")
            return {"years": 0, "level": "entry", "positions": [], "companies": []}

    async def extract_education(self, text: str) -> Dict[str, Any]:
        """Extract education information"""
        prompt = PromptTemplate(
            input_variables=["resume_text"],
            template="""
            Extract education information from this resume:
            
            {resume_text}
            
            Provide a JSON response with:
            {{
                "degrees": [list of degrees],
                "institutions": [list of schools/universities],
                "fields": [list of fields of study],
                "highest_degree": "<highest degree level>"
            }}
            
            Return only valid JSON, no explanations.
            """
        )
        
        try:
            response = await self.llm.ainvoke(prompt.format(resume_text=text[:3000]))
            import json
            return json.loads(response.strip())
        except Exception as e:
            logger.error(f"Education extraction failed: {e}")
            return {"degrees": [], "institutions": [], "fields": [], "highest_degree": ""}

    async def calculate_quality_score(self, text: str, skills: List[str], experience: Dict[str, Any]) -> Dict[str, float]:
        """Calculate resume quality metrics"""
        metrics = {}
        
        # Content completeness (0-1)
        content_score = min(len(text) / 2000, 1.0)  # Normalize to 2000 chars
        
        # Skills diversity (0-1)
        skills_score = min(len(skills) / 15, 1.0)  # Normalize to 15 skills
        
        # Experience level (0-1)
        experience_years = experience.get("years", 0)
        experience_score = min(experience_years / 10, 1.0)  # Normalize to 10 years
        
        # Overall quality
        overall_score = (content_score * 0.3 + skills_score * 0.4 + experience_score * 0.3)
        
        return {
            "content_score": round(content_score, 2),
            "skills_score": round(skills_score, 2),
            "experience_score": round(experience_score, 2),
            "overall_score": round(overall_score, 2)
        }
