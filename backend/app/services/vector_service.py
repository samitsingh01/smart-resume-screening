# backend/app/services/vector_service.py
import logging
from typing import List, Dict, Any, Optional
import chromadb
import numpy as np
from app.services.aws_bedrock import BedrockEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
import asyncio
from app.core.config import settings

logger = logging.getLogger(__name__)

class VectorService:
    def __init__(self):
        self.embeddings = None
        self.chroma_client = None
        self.resume_collection = None
        self.job_collection = None
        self.chunk_size = 1000
        self.chunk_overlap = 200

    async def initialize(self):
        """Initialize vector service"""
        try:
            # Initialize embeddings
            self.embeddings = BedrockEmbeddings(
                model_id="amazon.titan-embed-text-v1",
                region_name=settings.aws_region
            )
            
            # Initialize ChromaDB
            self.chroma_client = chromadb.PersistentClient(path=settings.chroma_db_path)
            
            # Create collections
            self.resume_collection = self.chroma_client.get_or_create_collection(
                name="resumes_v2",
                metadata={"description": "Enhanced resume embeddings"}
            )
            
            self.job_collection = self.chroma_client.get_or_create_collection(
                name="jobs_v2",
                metadata={"description": "Enhanced job embeddings"}
            )
            
            logger.info("Vector service initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize vector service: {e}")
            raise

    async def generate_embeddings(self, text: str) -> List[float]:
        """Generate embeddings for text"""
        try:
            return await asyncio.to_thread(self.embeddings.embed_query, text)
        except Exception as e:
            logger.error(f"Embedding generation failed: {e}")
            raise

    async def store_resume_embeddings(self, resume_id: str, content: str, metadata: Dict[str, Any]):
        """Store resume embeddings in vector database"""
        try:
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=self.chunk_size,
                chunk_overlap=self.chunk_overlap
            )
            
            chunks = text_splitter.split_text(content)
            embeddings = []
            
            # Generate embeddings for each chunk
            for chunk in chunks:
                embedding = await self.generate_embeddings(chunk)
                embeddings.append(embedding)
            
            # Store in ChromaDB
            ids = [f"{resume_id}_{i}" for i in range(len(chunks))]
            metadatas = [{**metadata, "chunk_index": i, "resume_id": resume_id} for i in range(len(chunks))]
            
            self.resume_collection.add(
                embeddings=embeddings,
                documents=chunks,
                ids=ids,
                metadatas=metadatas
            )
            
            logger.info(f"Stored {len(chunks)} chunks for resume {resume_id}")
            return len(chunks)
            
        except Exception as e:
            logger.error(f"Error storing resume embeddings: {e}")
            raise

    async def store_job_embeddings(self, job_id: str, job_data: Dict[str, Any]):
        """Store job embeddings in vector database"""
        try:
            # Combine job fields into searchable text
            job_text = f"""
            Title: {job_data['title']}
            Company: {job_data['company']}
            Description: {job_data['description']}
            Requirements: {' '.join(job_data.get('requirements', []))}
            Skills: {' '.join(job_data.get('required_skills', []))}
            Experience: {job_data.get('experience_level', '')}
            Location: {job_data.get('location', '')}
            Department: {job_data.get('department', '')}
            """
            
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=500,
                chunk_overlap=100
            )
            
            chunks = text_splitter.split_text(job_text)
            embeddings = []
            
            for chunk in chunks:
                embedding = await self.generate_embeddings(chunk)
                embeddings.append(embedding)
            
            ids = [f"{job_id}_{i}" for i in range(len(chunks))]
            metadatas = [{
                "job_id": job_id,
                "title": job_data['title'],
                "company": job_data['company'],
                "chunk_index": i,
                "original_job": job_data
            } for i in range(len(chunks))]
            
            self.job_collection.add(
                embeddings=embeddings,
                documents=chunks,
                ids=ids,
                metadatas=metadatas
            )
            
            logger.info(f"Stored {len(chunks)} chunks for job {job_id}")
            return len(chunks)
            
        except Exception as e:
            logger.error(f"Error storing job embeddings: {e}")
            raise

    async def search_similar_resumes(self, query: str, top_k: int = 20, filters: Optional[Dict] = None) -> Dict[str, Any]:
        """Search for similar resumes"""
        try:
            query_embedding = await self.generate_embeddings(query)
            
            search_kwargs = {
                "query_embeddings": [query_embedding],
                "n_results": top_k,
                "include": ["documents", "metadatas", "distances"]
            }
            
            if filters:
                search_kwargs["where"] = filters
            
            results = self.resume_collection.query(**search_kwargs)
            return results
            
        except Exception as e:
            logger.error(f"Error searching resumes: {e}")
            raise

    async def search_similar_jobs(self, query: str, top_k: int = 20) -> Dict[str, Any]:
        """Search for similar jobs"""
        try:
            query_embedding = await self.generate_embeddings(query)
            
            search_kwargs = {
                "query_embeddings": [query_embedding],
                "n_results": top_k,
                "include": ["documents", "metadatas", "distances"]
            }
            
            results = self.job_collection.query(**search_kwargs)
            return results
            
        except Exception as e:
            logger.error(f"Error searching jobs: {e}")
            raise

    async def get_resume_by_id(self, resume_id: str) -> Optional[Dict[str, Any]]:
        """Get resume chunks by ID"""
        try:
            results = self.resume_collection.get(
                where={"resume_id": resume_id},
                include=["documents", "metadatas"]
            )
            
            if results["documents"]:
                return {
                    "documents": results["documents"],
                    "metadatas": results["metadatas"]
                }
            return None
            
        except Exception as e:
            logger.error(f"Error getting resume {resume_id}: {e}")
            return None

    async def get_job_by_id(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get job chunks by ID"""
        try:
            results = self.job_collection.get(
                where={"job_id": job_id},
                include=["documents", "metadatas"]
            )
            
            if results["documents"]:
                return {
                    "documents": results["documents"],
                    "metadatas": results["metadatas"]
                }
            return None
            
        except Exception as e:
            logger.error(f"Error getting job {job_id}: {e}")
            return None

    async def update_resume_embeddings(self, resume_id: str, content: str, metadata: Dict[str, Any]):
        """Update existing resume embeddings"""
        try:
            # Delete existing embeddings
            await self.delete_resume_embeddings(resume_id)
            
            # Store new embeddings
            return await self.store_resume_embeddings(resume_id, content, metadata)
            
        except Exception as e:
            logger.error(f"Error updating resume embeddings: {e}")
            raise

    async def update_job_embeddings(self, job_id: str, job_data: Dict[str, Any]):
        """Update existing job embeddings"""
        try:
            # Delete existing embeddings
            await self.delete_job_embeddings(job_id)
            
            # Store new embeddings
            return await self.store_job_embeddings(job_id, job_data)
            
        except Exception as e:
            logger.error(f"Error updating job embeddings: {e}")
            raise

    async def delete_resume_embeddings(self, resume_id: str):
        """Delete resume embeddings from vector database"""
        try:
            # Get all chunks for this resume
            results = self.resume_collection.get(
                where={"resume_id": resume_id},
                include=["ids"]
            )
            
            if results["ids"]:
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
            
            if results["ids"]:
                self.job_collection.delete(ids=results["ids"])
                logger.info(f"Deleted embeddings for job {job_id}")
            
        except Exception as e:
            logger.error(f"Error deleting job embeddings: {e}")
            raise

    async def get_collection_stats(self) -> Dict[str, Any]:
        """Get statistics about the vector collections"""
        try:
            resume_count = self.resume_collection.count()
            job_count = self.job_collection.count()
            
            # Get unique resume and job counts
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
            return {}

    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on vector service"""
        try:
            # Test embedding generation
            test_embedding = await self.generate_embeddings("test query")
            
            # Get collection stats
            stats = await self.get_collection_stats()
            
            return {
                "status": "healthy",
                "embedding_model": "amazon.titan-embed-text-v1",
                "embedding_dimension": len(test_embedding) if test_embedding else 0,
                "collections": {
                    "resumes": {
                        "name": self.resume_collection.name,
                        "count": stats.get("total_resume_chunks", 0)
                    },
                    "jobs": {
                        "name": self.job_collection.name,
                        "count": stats.get("total_job_chunks", 0)
                    }
                },
                "statistics": stats
            }
            
        except Exception as e:
            logger.error(f"Vector service health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e)
            }
