"""Gemini Embeddings for document search - lightweight alternative to sentence-transformers."""
import requests
from typing import List
from app.config import settings


class GeminiEmbeddings:
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
        Embed a list of documents.
        
        Args:
            texts: List of text strings to embed
            
        Returns:
            List of embedding vectors
        """
        embeddings = []
        for text in texts:
            embedding = self._embed_text(text)
            embeddings.append(embedding)
        return embeddings
    
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

