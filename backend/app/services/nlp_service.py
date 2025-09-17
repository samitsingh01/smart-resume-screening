# backend/app/services/nlp_service.py
import re
import logging
from typing import List, Dict, Any
from app.services.aws_bedrock import BedrockLLM
from langchain.prompts import PromptTemplate
from app.core.config import settings

logger = logging.getLogger(__name__)

class NLPService:
    def __init__(self):
        self.llm = BedrockLLM(
            model_id="anthropic.claude-3-haiku-20240307-v1:0",
            region_name=settings.aws_region,
            model_kwargs={"max_tokens": 2000, "temperature": 0.1}
        )
        
        # Load spaCy model for NER (optional)
        self.nlp = None
        try:
            import spacy
            self.nlp = spacy.load("en_core_web_sm")
        except (ImportError, OSError):
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
            formatted_prompt = prompt.format(resume_text=text[:3000])
            response = await self.llm.ainvoke(formatted_prompt)
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
            'Machine Learning', 'Deep Learning', 'TensorFlow', 'PyTorch', 'Pandas',
            'FastAPI', 'Django', 'Flask', 'Vue.js', 'Angular', 'TypeScript', 'GraphQL',
            'Redis', 'Elasticsearch', 'Jenkins', 'CI/CD', 'Terraform', 'Ansible',
            'Microservices', 'REST API', 'GraphQL', 'OAuth', 'JWT', 'NGINX'
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
            formatted_prompt = prompt.format(resume_text=text[:3000])
            response = await self.llm.ainvoke(formatted_prompt)
            # Parse JSON response
            import json
            # Clean the response to extract JSON
            response = response.strip()
            if response.startswith('```json'):
                response = response[7:-3]
            elif response.startswith('```'):
                response = response[3:-3]
            
            return json.loads(response.strip())
        except Exception as e:
            logger.error(f"Experience extraction failed: {e}")
            return self._extract_experience_fallback(text)

    def _extract_experience_fallback(self, text: str) -> Dict[str, Any]:
        """Fallback experience extraction using pattern matching"""
        text_lower = text.lower()
        
        # Try to find years of experience
        years = 0
        year_patterns = [
            r'(\d+)\+?\s*years?\s*of\s*experience',
            r'(\d+)\+?\s*years?\s*experience',
            r'experience\s*:\s*(\d+)\+?\s*years?',
        ]
        
        for pattern in year_patterns:
            matches = re.findall(pattern, text_lower)
            if matches:
                years = max(int(match) for match in matches)
                break
        
        # Determine level based on years and keywords
        if years >= 7 or any(word in text_lower for word in ['senior', 'lead', 'principal', 'architect']):
            level = 'senior'
        elif years >= 3 or any(word in text_lower for word in ['mid-level', 'intermediate']):
            level = 'mid'
        else:
            level = 'entry'
        
        return {
            "years": years,
            "level": level,
            "positions": [],
            "companies": []
        }

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
            formatted_prompt = prompt.format(resume_text=text[:3000])
            response = await self.llm.ainvoke(formatted_prompt)
            import json
            # Clean the response to extract JSON
            response = response.strip()
            if response.startswith('```json'):
                response = response[7:-3]
            elif response.startswith('```'):
                response = response[3:-3]
            
            return json.loads(response.strip())
        except Exception as e:
            logger.error(f"Education extraction failed: {e}")
            return self._extract_education_fallback(text)

    def _extract_education_fallback(self, text: str) -> Dict[str, Any]:
        """Fallback education extraction using pattern matching"""
        education_keywords = [
            'bachelor', 'master', 'phd', 'doctorate', 'associate',
            'b.s.', 'b.a.', 'm.s.', 'm.a.', 'ph.d.', 'mba'
        ]
        
        degrees = []
        text_lower = text.lower()
        
        for keyword in education_keywords:
            if keyword in text_lower:
                degrees.append(keyword.title())
        
        return {
            "degrees": degrees,
            "institutions": [],
            "fields": [],
            "highest_degree": degrees[0] if degrees else ""
        }

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
        
        # Structure quality (check for common sections)
        structure_score = 0.0
        structure_keywords = ['experience', 'education', 'skills', 'summary', 'objective']
        text_lower = text.lower()
        
        for keyword in structure_keywords:
            if keyword in text_lower:
                structure_score += 0.2
        
        structure_score = min(structure_score, 1.0)
        
        # Overall quality
        overall_score = (
            content_score * 0.25 + 
            skills_score * 0.3 + 
            experience_score * 0.25 + 
            structure_score * 0.2
        )
        
        return {
            "content_score": round(content_score, 2),
            "skills_score": round(skills_score, 2),
            "experience_score": round(experience_score, 2),
            "structure_score": round(structure_score, 2),
            "overall_score": round(overall_score, 2)
        }

    async def extract_contact_info(self, text: str) -> Dict[str, Any]:
        """Extract contact information from resume"""
        contact_info = {}
        
        # Email pattern
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        emails = re.findall(email_pattern, text)
        if emails:
            contact_info['email'] = emails[0]
        
        # Phone pattern
        phone_pattern = r'[\+]?[1-9]?[\d\s\-\(\)]{10,}'
        phones = re.findall(phone_pattern, text)
        if phones:
            # Clean phone number
            phone = re.sub(r'[^\d+]', '', phones[0])
            if len(phone) >= 10:
                contact_info['phone'] = phones[0]
        
        # LinkedIn pattern
        linkedin_pattern = r'linkedin\.com/in/[\w\-]+'
        linkedin = re.findall(linkedin_pattern, text.lower())
        if linkedin:
            contact_info['linkedin'] = f"https://{linkedin[0]}"
        
        # GitHub pattern
        github_pattern = r'github\.com/[\w\-]+'
        github = re.findall(github_pattern, text.lower())
        if github:
            contact_info['github'] = f"https://{github[0]}"
        
        return contact_info

    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on NLP service"""
        try:
            # Test LLM connection
            test_prompt = "Say 'hello' in one word."
            response = await self.llm.ainvoke(test_prompt)
            
            return {
                "status": "healthy",
                "llm_model": self.llm.model_id,
                "spacy_available": self.nlp is not None,
                "test_response": response[:50] if response else "No response"
            }
            
        except Exception as e:
            logger.error(f"NLP service health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e)
            }
