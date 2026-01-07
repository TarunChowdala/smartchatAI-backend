"""Gemini Embeddings for document search - lightweight alternative to sentence-transformers."""
import requests
from typing import List
from langchain_core.embeddings import Embeddings
from app.config import settings


class GeminiEmbeddings(Embeddings):
    """
    Lightweight embeddings using Gemini API.
    Compatible with langchain's embedding interface.
    """
    
    def __init__(self):
        self.api_key = settings.gemini_api_key
        self.embedding_model = "text-embedding-004"
        self.api_url = f"{settings.gemini_api_url}/{self.embedding_model}:embedContent"
    
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """
        Embed a list of documents using batch API.
        
        Args:
            texts: List of text strings to embed
            
        Returns:
            List of embedding vectors
        """
        # Gemini supports up to 100 texts per batch
        batch_size = 100
        all_embeddings = []
        
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            batch_embeddings = self._embed_batch(batch)
            all_embeddings.extend(batch_embeddings)
        
        return all_embeddings
    
    def _embed_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Embed a batch of texts in a single API call.
        
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
            
            # Batch embedding request
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
                f"{settings.gemini_api_url}:batchEmbedContents",
                headers=headers,
                json=json_body,
                timeout=60  # Longer timeout for batch
            )
            response.raise_for_status()
            result = response.json()
            
            # Extract embeddings from batch response
            return [emb["embedding"]["values"] for emb in result["embeddings"]]
        except requests.exceptions.RequestException as e:
            # Fallback to sequential if batch fails
            print(f"Batch embedding failed, falling back to sequential: {e}")
            return [self._embed_text(text) for text in texts]
    
    def embed_query(self, text: str) -> List[float]:
        """
        Embed a single query text.
        
        Args:
            text: Query text to embed
            
        Returns:
            Embedding vector
        """
        return self._embed_text(text)
    
    def _embed_text(self, text: str) -> List[float]:
        """
        Get embedding for a single text using Gemini API.
        
        Args:
            text: Text to embed
            
        Returns:
            Embedding vector as list of floats
        """
        try:
            headers = {
                "x-goog-api-key": self.api_key,
                "Content-Type": "application/json"
            }
            json_body = {
                "model": f"models/{self.embedding_model}",
                "content": {"parts": [{"text": text}]}
            }
            
            response = requests.post(
                self.api_url,
                headers=headers,
                json=json_body,
                timeout=30
            )
            response.raise_for_status()
            result = response.json()
            return result["embedding"]["values"]
        except requests.exceptions.RequestException as e:
            raise ValueError(f"Failed to get embedding from Gemini API: {e}")

