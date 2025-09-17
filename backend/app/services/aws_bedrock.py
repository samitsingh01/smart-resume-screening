# backend/app/services/aws_bedrock.py
import boto3
import json
import logging
from typing import List, Dict, Any, Optional
from app.core.config import settings

logger = logging.getLogger(__name__)

class BedrockEmbeddings:
    """Custom Bedrock Embeddings class to replace langchain-aws"""
    
    def __init__(self, model_id: str = "amazon.titan-embed-text-v1", region_name: str = None):
        self.model_id = model_id
        self.region_name = region_name or settings.aws_region
        self.client = boto3.client(
            'bedrock-runtime',
            region_name=self.region_name,
            aws_access_key_id=settings.aws_access_key_id,
            aws_secret_access_key=settings.aws_secret_access_key
        )
    
    def embed_query(self, text: str) -> List[float]:
        """Generate embeddings for a single text"""
        try:
            body = json.dumps({"inputText": text})
            
            response = self.client.invoke_model(
                modelId=self.model_id,
                body=body,
                contentType='application/json',
                accept='application/json'
            )
            
            response_body = json.loads(response['body'].read())
            return response_body['embedding']
            
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            raise
    
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts"""
        return [self.embed_query(text) for text in texts]

class BedrockLLM:
    """Custom Bedrock LLM class to replace langchain-aws"""
    
    def __init__(self, model_id: str = "anthropic.claude-3-haiku-20240307-v1:0", region_name: str = None, model_kwargs: Dict = None):
        self.model_id = model_id
        self.region_name = region_name or settings.aws_region
        self.model_kwargs = model_kwargs or {"max_tokens": 2000, "temperature": 0.1}
        self.client = boto3.client(
            'bedrock-runtime',
            region_name=self.region_name,
            aws_access_key_id=settings.aws_access_key_id,
            aws_secret_access_key=settings.aws_secret_access_key
        )
    
    def invoke(self, prompt: str) -> str:
        """Invoke the LLM with a prompt"""
        try:
            if "claude-3" in self.model_id:
                # Claude 3 format
                body = json.dumps({
                    "anthropic_version": "bedrock-2023-05-31",
                    "max_tokens": self.model_kwargs.get("max_tokens", 2000),
                    "temperature": self.model_kwargs.get("temperature", 0.1),
                    "messages": [
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ]
                })
            else:
                # Other models format
                body = json.dumps({
                    "prompt": prompt,
                    "max_tokens_to_sample": self.model_kwargs.get("max_tokens", 2000),
                    "temperature": self.model_kwargs.get("temperature", 0.1)
                })
            
            response = self.client.invoke_model(
                modelId=self.model_id,
                body=body,
                contentType='application/json',
                accept='application/json'
            )
            
            response_body = json.loads(response['body'].read())
            
            if "claude-3" in self.model_id:
                return response_body['content'][0]['text']
            else:
                return response_body.get('completion', response_body.get('generated_text', ''))
            
        except Exception as e:
            logger.error(f"Error invoking LLM: {e}")
            raise
    
    async def ainvoke(self, prompt: str) -> str:
        """Async version of invoke"""
        return self.invoke(prompt)

def test_aws_connection() -> bool:
    """Test if AWS Bedrock is accessible"""
    try:
        client = boto3.client(
            'bedrock',
            region_name=settings.aws_region,
            aws_access_key_id=settings.aws_access_key_id,
            aws_secret_access_key=settings.aws_secret_access_key
        )
        # List available models to test connection
        response = client.list_foundation_models()
        return True
    except Exception as e:
        logger.error(f"AWS Bedrock connection failed: {e}")
        return False
