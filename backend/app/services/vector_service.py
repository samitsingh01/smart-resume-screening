import logging
from typing import List, Dict, Any, Optional
import chromadb
import numpy as np
import asyncio
from app.core.config import settings
import os

logger = logging.getLogger(__name__)

class VectorService:
    def __init__(self):
        self.embeddings = None
        self.chroma_client = None
        self.resume_collection = None
        self.job_collection = None
        self.chunk_size = 800
        self.chunk_overlap = 150

    async def initialize(self):
        """Initialize vector service"""
        try:
            # Ensure ChromaDB directory exists
            os.makedirs(settings.chroma_db_path, exist_ok=True)
            
            # Initialize ChromaDB with persistence
            self.chroma_client = chromadb.PersistentClient(path=settings.chroma_db_path)
            
            # Create collections with simple embeddings
            self.resume_collection = self.chroma_client.get_or_create_collection(
                name="resumes_simple",
                metadata={"description": "Simple resume embeddings"}
            )
            
            self.job_collection = self.chroma_client.get_or_create_collection(
                name="jobs_simple", 
                metadata={"description": "Simple job embeddings"}
            )
            
            logger.info("Vector service initialized successfully with basic embeddings")
        except Exception as e:
            logger.error(f"Failed to initialize vector service: {e}")
            raise

    def _generate_simple_embeddings(self, text: str) -> List[float]:
        """Generate simple embeddings using TF-IDF like approach"""
        try:
            # Simple word frequency based embeddings
            words = text.lower().split()
            
            # Common technical keywords for weighting
            tech_keywords = [
                'python', 'java', 'javascript', 'react', 'node', 'aws', 'docker', 
                'sql', 'database', 'api', 'web', 'mobile', 'software', 'engineer',
                'developer', 'manager', 'senior', 'junior', 'experience', 'project',
                'team', 'development', 'programming', 'coding', 'design', 'analysis'
            ]
            
            # Create a simple 100-dimensional embedding
            embedding = [0.0] * 100
            
            # Count word frequencies
            word_freq = {}
            for word in words:
                word_freq[word] = word_freq.get(word, 0) + 1
            
            # Fill embedding based on keywords presence and frequency
            for i, keyword in enumerate(tech_keywords):
                if i < 100:
                    if keyword in word_freq:
                        embedding[i] = min(word_freq[keyword] / len(words), 1.0)
            
            # Fill remaining dimensions with general word statistics
            for i in range(len(tech_keywords), 100):
                if i < len(words):
                    # Use character-based features
                    char_val = sum(ord(c) for c in words[i % len(words)]) % 100
                    embedding[i] = char_val / 100.0
                else:
                    embedding[i] = 0.1  # Small default value
            
            # Normalize the embedding
            norm = sum(x*x for x in embedding) ** 0.5
            if norm > 0:
                embedding = [x / norm for x in embedding]
            
            return embedding
            
        except Exception as e:
            logger.error(f"Simple embedding generation failed: {e}")
            # Return a default embedding
            return [0.01] * 100

    def _split_text_simple(self, text: str) -> List[str]:
        """Simple text splitting without langchain dependencies"""
        try:
            # Split by sentences first
            sentences = text.split('.')
            chunks = []
            current_chunk = ""
            
            for sentence in sentences:
                sentence = sentence.strip()
                if len(current_chunk) + len(sentence) < self.chunk_size:
                    current_chunk += sentence + ". "
                else:
                    if current_chunk:
                        chunks.append(current_chunk.strip())
                    current_chunk = sentence + ". "
            
            if current_chunk:
                chunks.append(current_chunk.strip())
            
            # Ensure we have at least one chunk
            if not chunks and text:
                chunks = [text[:self.chunk_size]]
            
            return chunks[:10]  # Limit to 10 chunks
            
        except Exception as e:
            logger.error(f"Text splitting failed: {e}")
            return [text[:self.chunk_size]] if text else [""]

    async def store_resume_embeddings(self, resume_id: str, content: str, metadata: Dict[str, Any]):
        """Store resume embeddings in vector database"""
        try:
            chunks = self._split_text_simple(content)
            embeddings = []
            documents = []
            ids = []
            metadatas = []
            
            # Generate embeddings for each chunk
            for i, chunk in enumerate(chunks):
                if chunk.strip():  # Only process non-empty chunks
                    embedding = self._generate_simple_embeddings(chunk)
                    embeddings.append(embedding)
                    documents.append(chunk)
                    ids.append(f"{resume_id}_{i}")
                    
                    chunk_metadata = {
                        **metadata,
                        "chunk_index": i,
                        "resume_id": resume_id,
                        "chunk_length": len(chunk)
                    }
                    metadatas.append(chunk_metadata)
            
            # Store in ChromaDB if we have valid data
            if embeddings and documents and ids:
                self.resume_collection.add(
                    embeddings=embeddings,
                    documents=documents,
                    ids=ids,
                    metadatas=metadatas
                )
                
                logger.info(f"Stored {len(chunks)} chunks for resume {resume_id}")
                return len(chunks)
            else:
                logger.warning(f"No valid chunks to store for resume {resume_id}")
                return 0
                
        except Exception as e:
            logger.error(f"Error storing resume embeddings: {e}")
            raise

    async def store_job_embeddings(self, job_id: str, job_data: Dict[str, Any]):
        """Store job embeddings in vector database"""
        try:
            # Combine job fields into searchable text
            job_text = f"""
            Title: {job_data.get('title', '')}
            Company: {job_data.get('company', '')}
            Description: {job_data.get('description', '')}
            Requirements: {' '.join(job_data.get('requirements', []))}
            Skills: {' '.join(job_data.get('required_skills', []))}
            Experience: {job_data.get('experience_level', '')}
            Location: {job_data.get('location', '')}
            Department: {job_data.get('department', '')}
            """.strip()
            
            chunks = self._split_text_simple(job_text)
            embeddings = []
            documents = []
            ids = []
            metadatas = []
            
            for i, chunk in enumerate(chunks):
                if chunk.strip():
                    embedding = self._generate_simple_embeddings(chunk)
                    embeddings.append(embedding)
                    documents.append(chunk)
                    ids.append(f"{job_id}_{i}")
                    
                    chunk_metadata = {
                        "job_id": job_id,
                        "title": job_data.get('title', ''),
                        "company": job_data.get('company', ''),
                        "chunk_index": i,
                        "experience_level": job_data.get('experience_level', ''),
                        "location": job_data.get('location', '')
                    }
                    metadatas.append(chunk_metadata)
            
            if embeddings and documents and ids:
                self.job_collection.add(
                    embeddings=embeddings,
                    documents=documents,
                    ids=ids,
                    metadatas=metadatas
                )
                
                logger.info(f"Stored {len(chunks)} chunks for job {job_id}")
                return len(chunks)
            else:
                logger.warning(f"No valid chunks to store for job {job_id}")
                return 0
                
        except Exception as e:
            logger.error(f"Error storing job embeddings: {e}")
            raise

    async def search_similar_resumes(self, query: str, top_k: int = 20, filters: Optional[Dict] = None) -> Dict[str, Any]:
        """Search for similar resumes"""
        try:
            query_embedding = self._generate_simple_embeddings(query)
            
            search_kwargs = {
                "query_embeddings": [query_embedding],
                "n_results": min(top_k, 100),  # Limit results
                "include": ["documents", "metadatas", "distances"]
            }
            
            if filters:
                # Convert filters to ChromaDB where clause
                where_clause = {}
                for key, value in filters.items():
                    if value:
                        where_clause[key] = {"$eq": value}
                if where_clause:
                    search_kwargs["where"] = where_clause
            
            results = self.resume_collection.query(**search_kwargs)
            
            # Process results to remove duplicates by resume_id
            unique_results = self._deduplicate_results(results)
            
            return unique_results
            
        except Exception as e:
            logger.error(f"Error searching resumes: {e}")
            return {"documents": [[]], "metadatas": [[]], "distances": [[]]}

    async def search_similar_jobs(self, query: str, top_k: int = 20) -> Dict[str, Any]:
        """Search for similar jobs"""
        try:
            query_embedding = self._generate_simple_embeddings(query)
            
            results = self.job_collection.query(
                query_embeddings=[query_embedding],
                n_results=min(top_k, 100),
                include=["documents", "metadatas", "distances"]
            )
            
            return results
            
        except Exception as e:
            logger.error(f"Error searching jobs: {e}")
            return {"documents": [[]], "metadatas": [[]], "distances": [[]]}

    def _deduplicate_results(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Remove duplicate results by resume_id, keeping the best score"""
        try:
            if not results.get("documents") or not results["documents"][0]:
                return results
            
            resume_best = {}  # resume_id -> (index, distance)
            
            # Find best result for each resume
            for i, (doc, metadata, distance) in enumerate(zip(
                results["documents"][0],
                results["metadatas"][0], 
                results["distances"][0]
            )):
                resume_id = metadata.get("resume_id")
                if resume_id:
                    if resume_id not in resume_best or distance < resume_best[resume_id][1]:
                        resume_best[resume_id] = (i, distance)
            
            # Build deduplicated results
            unique_indices = [idx for idx, _ in resume_best.values()]
            
            return {
                "documents": [[results["documents"][0][i] for i in unique_indices]],
                "metadatas": [[results["metadatas"][0][i] for i in unique_indices]],
                "distances": [[results["distances"][0][i] for i in unique_indices]]
            }
            
        except Exception as e:
            logger.error(f"Error deduplicating results: {e}")
            return results

    async def get_collection_stats(self) -> Dict[str, Any]:
        """Get statistics about the vector collections"""
        try:
            resume_count = self.resume_collection.count()
            job_count = self.job_collection.count()
            
            # Get unique counts
            resume_results = self.resume_collection.get(include=["metadatas"])
            job_results = self.job_collection.get(include=["metadatas"])
            
            unique_resumes = len(set(
                metadata.get("resume_id") 
                for metadata in resume_results.get("metadatas", [])
                if metadata.get("resume_id")
            ))
            
            unique_jobs = len(set(
                metadata.get("job_id")
                for metadata in job_results.get("metadatas", [])
                if metadata.get("job_id")
            ))
            
            return {
                "total_resume_chunks": resume_count,
                "total_job_chunks": job_count,
                "unique_resumes": unique_resumes,
                "unique_jobs": unique_jobs,
                "avg_chunks_per_resume": resume_count / unique_resumes if unique_resumes > 0 else 0,
                "avg_chunks_per_job": job_count / unique_jobs if unique_jobs > 0 else 0
            }
            
        except Exception as e:
            logger.error(f"Error getting collection stats: {e}")
            return {"error": str(e)}

    async def delete_resume_embeddings(self, resume_id: str):
        """Delete resume embeddings from vector database"""
        try:
            # Get all chunks for this resume
            results = self.resume_collection.get(
                where={"resume_id": resume_id},
                include=["ids"]
            )
            
            if results.get("ids"):
                self.resume_collection.delete(ids=results["ids"])
                logger.info(f"Deleted embeddings for resume {resume_id}")
            
        except Exception as e:
            logger.error(f"Error deleting resume embeddings: {e}")
            raise

    async def delete_job_embeddings(self, job_id: str):
        """Delete job embeddings from vector database"""
        try:
            # Get all chunks for this job
            results = self.job_collection.get(
                where={"job_id": job_id},
                include=["ids"]
            )
            
            if results.get("ids"):
                self.job_collection.delete(ids=results["ids"])
                logger.info(f"Deleted embeddings for job {job_id}")
            
        except Exception as e:
            logger.error(f"Error deleting job embeddings: {e}")
            raise

    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on vector service"""
        try:
            # Test embedding generation
            test_embedding = self._generate_simple_embeddings("test query")
            
            # Get collection stats
            stats = await self.get_collection_stats()
            
            return {
                "status": "healthy",
                "embedding_model": "simple_tfidf",
                "embedding_dimension": len(test_embedding) if test_embedding else 0,
                "collections": {
                    "resumes": {
                        "name": self.resume_collection.name if self.resume_collection else "none",
                        "count": stats.get("total_resume_chunks", 0)
                    },
                    "jobs": {
                        "name": self.job_collection.name if self.job_collection else "none", 
                        "count": stats.get("total_job_chunks", 0)
                    }
                },
                "statistics": stats
            }
            
        except Exception as e:
            logger.error(f"Vector service health check failed: {e}")
            return {"status": "unhealthy", "error": str(e)}
