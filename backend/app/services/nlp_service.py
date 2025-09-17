import re
import logging
from typing import List, Dict, Any
import json

logger = logging.getLogger(__name__)

class NLPService:
    def __init__(self):
        # Try to load spaCy model but don't fail if it's not available
        self.nlp = None
        try:
            import spacy
            self.nlp = spacy.load("en_core_web_sm")
            logger.info("spaCy model loaded successfully")
        except (ImportError, OSError) as e:
            logger.warning(f"spaCy model not found: {e}, using basic text processing")
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
        """Extract skills from resume text using pattern matching"""
        try:
            # Common technical skills database
            common_skills = [
                # Programming Languages
                'Python', 'Java', 'JavaScript', 'TypeScript', 'C++', 'C#', 'PHP', 'Ruby', 'Go', 'Rust',
                'Swift', 'Kotlin', 'Scala', 'R', 'MATLAB', 'Perl', 'Shell', 'Bash',
                
                # Web Technologies
                'HTML', 'CSS', 'React', 'Angular', 'Vue.js', 'Node.js', 'Express.js', 'Django', 'Flask',
                'Spring', 'Laravel', 'Ruby on Rails', 'ASP.NET', 'jQuery', 'Bootstrap', 'Sass', 'Less',
                
                # Databases
                'MySQL', 'PostgreSQL', 'MongoDB', 'Redis', 'Elasticsearch', 'SQLite', 'Oracle', 'SQL Server',
                'Cassandra', 'Neo4j', 'DynamoDB', 'CouchDB', 'InfluxDB',
                
                # Cloud & DevOps
                'AWS', 'Azure', 'Google Cloud', 'GCP', 'Docker', 'Kubernetes', 'Jenkins', 'CI/CD',
                'Terraform', 'Ansible', 'Chef', 'Puppet', 'GitLab CI', 'GitHub Actions', 'CircleCI',
                
                # Tools & Frameworks
                'Git', 'SVN', 'JIRA', 'Confluence', 'Slack', 'Trello', 'Agile', 'Scrum', 'Kanban',
                'REST API', 'GraphQL', 'SOAP', 'gRPC', 'Microservices', 'OAuth', 'JWT', 'NGINX', 'Apache',
                
                # Data Science & ML
                'Machine Learning', 'Deep Learning', 'TensorFlow', 'PyTorch', 'Keras', 'Scikit-learn',
                'Pandas', 'NumPy', 'Matplotlib', 'Seaborn', 'Jupyter', 'Apache Spark', 'Hadoop',
                'Data Mining', 'Statistics', 'Neural Networks', 'Computer Vision', 'NLP',
                
                # Mobile Development
                'iOS', 'Android', 'React Native', 'Flutter', 'Xamarin', 'Ionic', 'Cordova',
                
                # Operating Systems
                'Linux', 'Windows', 'macOS', 'Unix', 'Ubuntu', 'CentOS', 'RHEL',
                
                # Other Technical
                'Blockchain', 'Cryptocurrency', 'IoT', 'AR/VR', 'Game Development', 'Unity', 'Unreal Engine'
            ]
            
            found_skills = []
            text_lower = text.lower()
            
            # Look for exact matches and variations
            for skill in common_skills:
                skill_lower = skill.lower()
                if skill_lower in text_lower:
                    found_skills.append(skill)
                    continue
                
                # Check variations
                variations = [
                    skill_lower.replace('.', ''),
                    skill_lower.replace(' ', ''),
                    skill_lower.replace('-', ' '),
                    skill_lower.replace('_', ' ')
                ]
                
                for variation in variations:
                    if variation in text_lower:
                        found_skills.append(skill)
                        break
            
            # Remove duplicates while preserving order
            unique_skills = []
            for skill in found_skills:
                if skill not in unique_skills:
                    unique_skills.append(skill)
            
            return unique_skills[:20]  # Limit to top 20 skills
            
        except Exception as e:
            logger.error(f"Skill extraction failed: {e}")
            return []

    async def extract_experience(self, text: str) -> Dict[str, Any]:
        """Extract experience information using pattern matching"""
        try:
            text_lower = text.lower()
            
            # Try to find years of experience
            years = 0
            year_patterns = [
                r'(\d+)\+?\s*years?\s*of\s*experience',
                r'(\d+)\+?\s*years?\s*experience',
                r'experience\s*[:\-]?\s*(\d+)\+?\s*years?',
                r'(\d+)\+?\s*yrs?\s*experience',
                r'over\s*(\d+)\s*years?',
                r'more\s*than\s*(\d+)\s*years?'
            ]
            
            for pattern in year_patterns:
                matches = re.findall(pattern, text_lower)
                if matches:
                    # Take the maximum years found
                    years = max(int(match) for match in matches if match.isdigit())
                    break
            
            # Extract job titles and companies using common patterns
            positions = []
            companies = []
            
            # Look for job title patterns
            title_patterns = [
                r'(?:software|web|mobile|front[- ]?end|back[- ]?end|full[- ]?stack)\s+(?:engineer|developer|programmer)',
                r'(?:senior|junior|lead|principal)\s+(?:engineer|developer|programmer|architect)',
                r'(?:data|machine learning|ml|ai)\s+(?:scientist|engineer|analyst)',
                r'(?:product|project|program)\s+manager',
                r'(?:devops|site reliability)\s+engineer',
                r'(?:qa|quality assurance|test)\s+(?:engineer|analyst)',
                r'(?:ui|ux|user experience|user interface)\s+(?:designer|engineer)',
                r'(?:business|data|systems)\s+analyst'
            ]
            
            for pattern in title_patterns:
                matches = re.findall(pattern, text_lower)
                positions.extend(matches)
            
            # Extract company names (basic pattern - look for "at Company" or "@ Company")
            company_patterns = [
                r'(?:at|@)\s+([A-Z][a-zA-Z\s&\.]{2,30}(?:Inc|Corp|LLC|Ltd|Company)?)',
                r'(?:worked for|employed by)\s+([A-Z][a-zA-Z\s&\.]{2,30})'
            ]
            
            for pattern in company_patterns:
                matches = re.findall(pattern, text)
                companies.extend([match.strip() for match in matches if len(match.strip()) > 3])
            
            # Determine experience level based on years and keywords
            level_keywords = {
                'entry': ['entry', 'junior', 'associate', 'trainee', 'intern', 'graduate', 'fresher', 'beginner'],
                'mid': ['mid-level', 'intermediate', 'experienced', 'specialist', 'developer', 'analyst', 'consultant'],
                'senior': ['senior', 'lead', 'principal', 'expert', 'architect', 'manager', 'director', 'head'],
                'lead': ['lead', 'principal', 'director', 'manager', 'head', 'chief', 'vp', 'vice president', 'cto', 'ceo']
            }
            
            level = 'entry'  # default
            
            # Check for explicit level keywords
            for level_name, keywords in level_keywords.items():
                if any(keyword in text_lower for keyword in keywords):
                    level = level_name
                    break
            
            # Override based on years if no explicit keywords found
            if years >= 8:
                level = 'senior' if level == 'entry' else level
            elif years >= 4:
                level = 'mid' if level == 'entry' else level
            
            return {
                "years": years,
                "level": level,
                "positions": list(set(positions))[:5],  # Top 5 unique positions
                "companies": list(set(companies))[:5]  # Top 5 unique companies
            }
            
        except Exception as e:
            logger.error(f"Experience extraction failed: {e}")
            return {"years": 0, "level": "entry", "positions": [], "companies": []}

    async def extract_education(self, text: str) -> Dict[str, Any]:
        """Extract education information using pattern matching"""
        try:
            education_keywords = {
                'degrees': [
                    'bachelor', 'master', 'phd', 'doctorate', 'associate', 'diploma',
                    'b.s.', 'b.a.', 'm.s.', 'm.a.', 'ph.d.', 'mba', 'md', 'jd',
                    'b.tech', 'm.tech', 'b.e.', 'm.e.', 'bsc', 'msc', 'bca', 'mca'
                ],
                'fields': [
                    'computer science', 'software engineering', 'information technology',
                    'electrical engineering', 'mechanical engineering', 'civil engineering',
                    'business administration', 'mathematics', 'physics', 'chemistry',
                    'data science', 'artificial intelligence', 'machine learning',
                    'cybersecurity', 'information systems', 'marketing', 'finance'
                ],
                'institutions': [
                    'university', 'college', 'institute', 'school', 'academy'
                ]
            }
            
            degrees = []
            fields = []
            institutions = []
            
            text_lower = text.lower()
            
            # Find degrees
            for degree in education_keywords['degrees']:
                if degree in text_lower:
                    degrees.append(degree.title())
            
            # Find fields of study
            for field in education_keywords['fields']:
                if field in text_lower:
                    fields.append(field.title())
            
            # Basic institution extraction
            institution_patterns = [
                r'([A-Z][a-zA-Z\s]{3,30}(?:University|College|Institute))',
                r'(?:from|at)\s+([A-Z][a-zA-Z\s]{3,30})'
            ]
            
            for pattern in institution_patterns:
                matches = re.findall(pattern, text)
                institutions.extend([match.strip() for match in matches if len(match.strip()) > 5])
            
            # Determine highest degree
            degree_hierarchy = ['associate', 'bachelor', 'master', 'phd', 'doctorate']
            highest_degree = ""
            
            for degree in reversed(degree_hierarchy):
                if any(degree in d.lower() for d in degrees):
                    highest_degree = degree.title()
                    break
            
            return {
                "degrees": list(set(degrees))[:3],
                "institutions": list(set(institutions))[:3],
                "fields": list(set(fields))[:3],
                "highest_degree": highest_degree
            }
            
        except Exception as e:
            logger.error(f"Education extraction failed: {e}")
            return {"degrees": [], "institutions": [], "fields": [], "highest_degree": ""}

    async def calculate_quality_score(self, text: str, skills: List[str], experience: Dict[str, Any]) -> Dict[str, float]:
        """Calculate resume quality metrics"""
        try:
            metrics = {}
            
            # Content completeness (0-1)
            content_score = min(len(text) / 1500, 1.0)
            
            # Skills diversity (0-1)
            skills_score = min(len(skills) / 12, 1.0)
            
            # Experience level (0-1)
            experience_years = experience.get("years", 0)
            experience_score = min(experience_years / 8, 1.0)
            
            # Structure quality (check for common sections)
            structure_keywords = ['experience', 'education', 'skills', 'summary', 'objective', 'projects']
            structure_score = 0.0
            text_lower = text.lower()
            
            for keyword in structure_keywords:
                if keyword in text_lower:
                    structure_score += 1.0 / len(structure_keywords)
            
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
            
        except Exception as e:
            logger.error(f"Quality score calculation failed: {e}")
            return {
                "content_score": 0.5,
                "skills_score": 0.5,
                "experience_score": 0.5,
                "structure_score": 0.5,
                "overall_score": 0.5
            }

    async def extract_contact_info(self, text: str) -> Dict[str, Any]:
        """Extract contact information from resume"""
        try:
            contact_info = {}
            
            # Email pattern
            email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
            emails = re.findall(email_pattern, text)
            if emails:
                contact_info['email'] = emails[0]
            
            # Phone pattern
            phone_patterns = [
                r'[\+]?[1-9]?[\d\s\-\(\)]{10,}',
                r'\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b',
                r'\(\d{3}\)\s*\d{3}[-.\s]?\d{4}'
            ]
            
            for pattern in phone_patterns:
                phones = re.findall(pattern, text)
                if phones:
                    # Clean phone number
                    phone = re.sub(r'[^\d+]', '', phones[0])
                    if len(phone) >= 10:
                        contact_info['phone'] = phones[0]
                        break
            
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
            
        except Exception as e:
            logger.error(f"Contact info extraction failed: {e}")
            return {}

    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on NLP service"""
        try:
            return {
                "status": "healthy",
                "spacy_available": self.nlp is not None,
                "features": [
                    "skill_extraction",
                    "experience_extraction", 
                    "education_extraction",
                    "contact_extraction",
                    "quality_scoring"
                ]
            }
        except Exception as e:
            logger.error(f"NLP service health check failed: {e}")
            return {"status": "unhealthy", "error": str(e)}

