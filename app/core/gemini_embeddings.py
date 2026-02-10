"""Gemini Embeddings using Google's Gemini API (lightweight, no model download)."""
import requests
from typing import List, Optional
from langchain_core.embeddings import Embeddings
from app.config import settings


class GeminiEmbeddings(Embeddings):
    """
    Embeddings using Gemini API (gemini-embedding-001).
    Lightweight - no model download required, uses API only.
    Compatible with langchain's embedding interface.
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize embeddings with Gemini API.
        
        Args:
            api_key: Gemini API key (uses settings key if not provided)
        """
        self.api_key = api_key or settings.gemini_api_key
        self.embedding_model = "gemini-embedding-001"
        self.api_url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.embedding_model}:embedContent"
        self.batch_api_url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.embedding_model}:batchEmbedContents"
        
        if not self.api_key:
            raise ValueError("Gemini API key is not set. Set GEMINI_API_KEY in environment variables.")
        
        print(f"Using Gemini API for embeddings ({self.embedding_model})")
    
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """
        Embed a list of documents using Gemini API.
        
        Args:
            texts: List of text strings to embed
            
        Returns:
            List of embedding vectors
        """
        # Use sequential API calls (more reliable than batch API)
        # Can be optimized later if batch API format is confirmed
        return [self._embed_text(text) for text in texts]
    
    def embed_query(self, text: str) -> List[float]:
        """
        Embed a single query text using Gemini API.
        
        Args:
            text: Query text to embed
            
        Returns:
            Embedding vector
        """
        return self._embed_text(text)
    
    def _embed_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Embed a batch of texts using batch API (more efficient).
        
        Args:
            texts: List of text strings to embed (max 100)
            
        Returns:
            List of embedding vectors
        """
        try:
            headers = {
                "x-goog-api-key": self.api_key,
                "Content-Type": "application/json"
            }
            
            # Batch embedding request format
            json_body = {
                "requests": [
                    {
                        "model": f"models/{self.embedding_model}",
                        "content": {"parts": [{"text": text}]}
                    }
                    for text in texts
                ]
            }
            
            response = requests.post(
                self.batch_api_url,
                headers=headers,
                json=json_body,
                timeout=60
            )
            
            if response.status_code == 404:
                raise ValueError(
                    f"Embedding model not found. Response: {response.text}"
                )
            
            response.raise_for_status()
            result = response.json()
            
            # Extract embeddings from batch response
            # Response format: {"embeddings": [{"embedding": {"values": [...]}}, ...]}
            if "embeddings" not in result:
                raise ValueError(f"Unexpected batch API response format: {result}")
            
            embeddings_list = []
            for emb in result["embeddings"]:
                if "embedding" not in emb:
                    raise ValueError(f"Missing 'embedding' key in response: {emb}. Full response: {result}")
                if "values" not in emb["embedding"]:
                    raise ValueError(f"Missing 'values' key in embedding: {emb['embedding']}. Full response: {result}")
                embeddings_list.append(emb["embedding"]["values"])
            
            return embeddings_list
        except (KeyError, ValueError) as e:
            # If it's a parsing error, fallback to sequential
            error_msg = str(e)
            print(f"Batch embedding parsing failed, falling back to sequential: {error_msg}")
            return [self._embed_text(text) for text in texts]
        except requests.exceptions.RequestException as e:
            # Fallback to sequential if batch fails
            error_detail = str(e)
            if hasattr(e, 'response') and e.response is not None:
                error_detail += f" - Response: {e.response.text}"
            print(f"Batch embedding API call failed, falling back to sequential: {error_detail}")
            return [self._embed_text(text) for text in texts]
    
    def _embed_text(self, text: str) -> List[float]:
        """
        Embed a single text using Gemini API.
        
        Args:
            text: Text to embed
            
        Returns:
            Embedding vector as list of floats
        """
        if not self.api_key:
            raise ValueError("Gemini API key is not set")
        
        try:
            headers = {
                "x-goog-api-key": self.api_key,
                "Content-Type": "application/json"
            }
            
            json_body = {
                "content": {"parts": [{"text": text}]}
            }
            
            response = requests.post(
                self.api_url,
                headers=headers,
                json=json_body,
                timeout=30
            )
            
            if response.status_code == 404:
                raise ValueError(
                    f"Embedding model not found. Check if '{self.embedding_model}' is available. "
                    f"Response: {response.text}"
                )
            
            response.raise_for_status()
            result = response.json()
            
            # Check response structure and provide detailed error
            if "embedding" not in result:
                raise ValueError(
                    f"Missing 'embedding' key in API response. "
                    f"Response keys: {list(result.keys())}. "
                    f"Full response: {result}"
                )
            
            if "values" not in result["embedding"]:
                raise ValueError(
                    f"Missing 'values' key in embedding. "
                    f"Embedding keys: {list(result['embedding'].keys())}. "
                    f"Full response: {result}"
                )
            
            return result["embedding"]["values"]
        except requests.exceptions.RequestException as e:
            error_detail = str(e)
            if hasattr(e, 'response') and e.response is not None:
                error_detail += f" - Response: {e.response.text}"
            raise ValueError(f"Failed to get embedding from Gemini API: {error_detail}")
