"""Document processing service for RAG operations with Firestore metadata."""
import os
import uuid
from pathlib import Path
from typing import Optional
from fastapi import HTTPException, BackgroundTasks
from langchain_community.vectorstores import FAISS
from app.core.gemini_embeddings import GeminiEmbeddings
from langchain_community.document_loaders import (
    PyPDFLoader,
    TextLoader,
    Docx2txtLoader,
    UnstructuredPowerPointLoader,
    UnstructuredExcelLoader
)
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_core.prompts import PromptTemplate
import requests
from firebase_admin import firestore
from app.config import settings
from app.db.firestore_client import get_firestore_db


class DocumentService:
    """Service for document processing and Q&A with Firestore metadata."""
    
    def __init__(self):
        self.api_key = settings.gemini_api_key
        self.model = settings.gemini_model
        self.api_url = settings.gemini_api_url
        self.temp_dir = settings.temp_docs_dir
        self.db = get_firestore_db()
        
        # Initialize embeddings using Gemini API (lightweight, no PyTorch needed)
        self.embeddings = GeminiEmbeddings()
        
        # Storage: key format is "user_id_document_id" for multi-user support
        self.vectorstores: dict[str, FAISS] = {}
        self.processing_status: dict[str, bool] = {}
        
        # RAG prompt template
        self.qa_prompt = PromptTemplate(
            template="""You are a precise AI assistant that answers questions using ONLY the provided context.

CRITICAL RULES:
1. Answer ONLY using information from the context below
2. If the context does not contain enough information to answer, respond naturally with variations like:
   - "I don't see that information in the provided documents. Could you rephrase your question or ask about something else?"
   - "The documents don't seem to cover this topic. Feel free to ask about other aspects of the content."
   - "I couldn't locate an answer to that in the given context. What else would you like to know?"
   - "This information isn't available in the documents. Try asking about a different aspect of the content."
   - "The provided context doesn't include details about this. Please rephrase or ask another question."
   Vary your wording naturally while conveying the same meaning.
3. Do NOT use any external knowledge or make assumptions beyond what's in the context
4. Do NOT mention that you're an AI, assistant, or reference the context itself
5. Provide clear, concise, and accurate answers
6. If asked about something not in the context, politely decline with varied wording and suggest asking about the document content

Context:
{context}

Question: {question}

Answer:""",
            input_variables=["context", "question"]
        )
        
        self.supported_extensions = {
            '.pdf': PyPDFLoader,
            '.txt': TextLoader,
            '.docx': Docx2txtLoader,
            '.doc': Docx2txtLoader,
            '.ppt': UnstructuredPowerPointLoader,
            '.pptx': UnstructuredPowerPointLoader,
            '.xls': UnstructuredExcelLoader,
            '.xlsx': UnstructuredExcelLoader
        }
    
    def get_document_loader(self, file_path: str):
        """
        Get appropriate document loader for file type.
        
        Args:
            file_path: Path to document file
            
        Returns:
            Document loader instance
            
        Raises:
            HTTPException: If file type is unsupported
        """
        file_extension = Path(file_path).suffix.lower()
        if file_extension not in self.supported_extensions:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file type. Supported types are: {', '.join(self.supported_extensions.keys())}"
            )
        return self.supported_extensions[file_extension](file_path)
    
    def _get_chunk_size(self, doc_length: int) -> tuple[int, int]:
        """Adaptive chunking based on document size."""
        if doc_length < 5000:
            return 500, 100
        elif doc_length < 50000:
            return 1000, 200
        else:
            return 1500, 300
    
    def process_document(self, document_id: str, user_id: str, filename: str, file_path: str) -> None:
        """
        Process document in background: load, split, embed, and create vector store.
        Stores metadata in Firestore and creates FAISS vectorstore.
        
        Args:
            document_id: Unique document identifier
            user_id: User ID from Firebase token
            filename: Original filename
            file_path: Path to document file
        """
        store_key = f"{user_id}_{document_id}"
        try:
            loader = self.get_document_loader(file_path)
            documents = loader.load()
            
            if not documents:
                raise Exception("No content could be extracted from the document")
            
            # Adaptive chunking
            total_length = sum(len(doc.page_content) for doc in documents)
            chunk_size, chunk_overlap = self._get_chunk_size(total_length)
            
            splitter = RecursiveCharacterTextSplitter(
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                length_function=len,
                separators=["\n\n", "\n", ". ", " ", ""]
            )
            texts = splitter.split_documents(documents)
            
            if not texts:
                raise Exception("Document splitting resulted in no chunks")
            
            # Add metadata to chunks
            for i, chunk in enumerate(texts):
                chunk.metadata.update({
                    "user_id": user_id,
                    "document_id": document_id,
                    "filename": filename,
                    "chunk_index": i
                })
            
            # Create FAISS vectorstore using pre-initialized embeddings
            vectorstore = FAISS.from_documents(texts, self.embeddings)
            
            # Store vectorstore
            self.vectorstores[store_key] = vectorstore
            
            # Save metadata to Firestore
            doc_ref = self.db.collection("documents").document(document_id)
            doc_ref.set({
                "document_id": document_id,
                "user_id": user_id,
                "filename": filename,
                "chunks_count": len(texts),
                "total_length": total_length,
                "chunk_size": chunk_size,
                "chunk_overlap": chunk_overlap,
                "status": "ready",
                "created_at": firestore.SERVER_TIMESTAMP,
                "updated_at": firestore.SERVER_TIMESTAMP
            })
            
        except Exception as e:
            error_msg = str(e)
            print(f"[Error processing doc {document_id}]: {error_msg}")
            
            # Update Firestore with error
            doc_ref = self.db.collection("documents").document(document_id)
            doc_ref.update({
                "status": "error",
                "error_message": error_msg,
                "updated_at": firestore.SERVER_TIMESTAMP
            })
        finally:
            self.processing_status[store_key] = False
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                except Exception as e:
                    print(f"[Warning] Could not delete temp file {file_path}: {e}")
    
    def upload_document(
        self,
        file_content: bytes,
        filename: str,
        user_id: str,
        background_tasks: BackgroundTasks
    ) -> dict:
        """
        Upload and process document with user_id from token.
        
        Args:
            file_content: File content bytes
            filename: Original filename
            user_id: User ID from Firebase token (never from request)
            background_tasks: FastAPI background tasks
            
        Returns:
            Upload response with document_id
            
        Raises:
            HTTPException: If file is invalid
        """
        if not filename:
            raise HTTPException(status_code=400, detail="No file provided")
        
        file_extension = Path(filename).suffix.lower()
        if file_extension not in self.supported_extensions:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file type. Supported types are: {', '.join(self.supported_extensions.keys())}"
            )
        
        if not file_content:
            raise HTTPException(status_code=400, detail="Empty file uploaded")
        
        if len(file_content) > settings.max_upload_size:
            raise HTTPException(
                status_code=400,
                detail=f"File too large. Max size: {settings.max_upload_size / 1024 / 1024}MB"
            )
        
        document_id = str(uuid.uuid4())
        store_key = f"{user_id}_{document_id}"
        self.processing_status[store_key] = True
        
        os.makedirs(self.temp_dir, exist_ok=True)
        file_location = os.path.join(self.temp_dir, f"{document_id}_{filename}")
        
        with open(file_location, "wb") as f:
            f.write(file_content)
        
        # Create initial Firestore document
        doc_ref = self.db.collection("documents").document(document_id)
        doc_ref.set({
            "document_id": document_id,
            "user_id": user_id,
            "filename": filename,
            "status": "processing",
            "created_at": firestore.SERVER_TIMESTAMP
        })
        
        background_tasks.add_task(
            self.process_document,
            document_id,
            user_id,
            filename,
            file_location
        )
        
        return {
            "message": "File uploaded successfully. Processing in background...",
            "task_id": document_id,
            "document_id": document_id,
            "status": "processing"
        }
    
    def get_status(self, document_id: str, user_id: str) -> dict:
        """
        Get processing status for a document with user verification.
        
        Args:
            document_id: Document identifier
            user_id: User ID from token (for verification)
            
        Returns:
            Status response
            
        Raises:
            HTTPException: If document_id is invalid or user not authorized
        """
        store_key = f"{user_id}_{document_id}"
        
        # Check Firestore
        doc_ref = self.db.collection("documents").document(document_id)
        doc = doc_ref.get()
        
        if not doc.exists:
            raise HTTPException(status_code=404, detail="Document not found")
        
        doc_data = doc.to_dict()
        
        # Verify ownership
        if doc_data.get("user_id") != user_id:
            raise HTTPException(status_code=403, detail="Not authorized to access this document")
        
        # Check if vectorstore exists
        is_ready = store_key in self.vectorstores and not self.processing_status.get(store_key, False)
        
        return {
            "processing": self.processing_status.get(store_key, False),
            "ready": is_ready,
            "status": "ready" if is_ready else doc_data.get("status", "processing"),
            "filename": doc_data.get("filename"),
            "chunks_count": doc_data.get("chunks_count"),
            "error": doc_data.get("error_message")
        }
    
    def call_gemini_llm(self, prompt: str) -> str:
        """
        Call Gemini API for LLM response.
        
        Args:
            prompt: Input prompt
            
        Returns:
            LLM response text
        """
        headers = {
            "x-goog-api-key": self.api_key,
            "Content-Type": "application/json"
        }
        json_body = {
            "contents": [
                {"parts": [{"text": prompt}]}
            ]
        }
        
        try:
            response = requests.post(
                f"{self.api_url}/{self.model}:generateContent",
                headers=headers,
                json=json_body,
                timeout=30
            )
            response.raise_for_status()
            data = response.json()
            return data["candidates"][0]["content"]["parts"][0]["text"]
        except Exception as e:
            print("Gemini LLM error:", e)
            return "Error: Could not get response from Gemini"
    
    def ask_question(
        self,
        question: str,
        document_id: str,
        user_id: str,
        use_mmr: bool = True,
        k: int = 5
    ) -> dict:
        """
        Ask question about uploaded document using advanced RAG retrieval.
        
        Args:
            question: User question
            document_id: Document identifier
            user_id: User ID from token (for verification)
            use_mmr: Use Max Marginal Relevance retrieval
            k: Number of chunks to retrieve
            
        Returns:
            Question and answer response with source documents
            
        Raises:
            HTTPException: If document is still processing or invalid
        """
        store_key = f"{user_id}_{document_id}"
        
        # Check if document is still processing
        if self.processing_status.get(store_key):
            raise HTTPException(
                status_code=202,
                detail="Document is still processing. Please wait a moment and try again."
            )
        
        # Get vectorstore
        vector_store = self.vectorstores.get(store_key)
        if not vector_store:
            # Verify document exists and belongs to user
            doc_ref = self.db.collection("documents").document(document_id)
            doc = doc_ref.get()
            if not doc.exists:
                raise HTTPException(status_code=404, detail="Document not found")
            doc_data = doc.to_dict()
            if doc_data.get("user_id") != user_id:
                raise HTTPException(status_code=403, detail="Not authorized to access this document")
            raise HTTPException(status_code=404, detail="Document vectorstore not found. Processing may have failed.")
        
        # Use advanced retrieval (MMR or similarity)
        if use_mmr:
            docs = vector_store.max_marginal_relevance_search(
                question,
                k=k,
                fetch_k=k * 4,
                lambda_mult=0.5
            )
        else:
            docs = vector_store.similarity_search(question, k=k)
        
        if not docs:
            return {
                "question": question,
                "answer": "I couldn't find any relevant information in the documents to answer this question.",
                "chunks_used": 0,
                "source_documents": []
            }
        
        # Format context
        context = "\n\n".join([doc.page_content for doc in docs])
        
        # Format prompt using template
        prompt = self.qa_prompt.format(context=context, question=question)
        
        # Call LLM
        answer = self.call_gemini_llm(prompt)
        
        return {
            "question": question,
            "answer": answer,
            "chunks_used": len(docs),
            "source_documents": [
                {
                    "content": doc.page_content[:200] + "..." if len(doc.page_content) > 200 else doc.page_content,
                    "metadata": {
                        "filename": doc.metadata.get("filename"),
                        "chunk_index": doc.metadata.get("chunk_index")
                    }
                }
                for doc in docs
            ]
        }
    
    def delete_document(self, document_id: str, user_id: str) -> dict:
        """
        Delete document and its vectorstore.
        
        Args:
            document_id: Document identifier
            user_id: User ID from token (for verification)
            
        Returns:
            Deletion confirmation
            
        Raises:
            HTTPException: If document not found or user not authorized
        """
        store_key = f"{user_id}_{document_id}"
        
        # Check Firestore
        doc_ref = self.db.collection("documents").document(document_id)
        doc = doc_ref.get()
        
        if not doc.exists:
            raise HTTPException(status_code=404, detail="Document not found")
        
        doc_data = doc.to_dict()
        
        # Verify ownership
        if doc_data.get("user_id") != user_id:
            raise HTTPException(status_code=403, detail="Not authorized to delete this document")
        
        # Delete from Firestore
        doc_ref.delete()
        
        # Delete from RAM (vectorstore)
        self.vectorstores.pop(store_key, None)
        self.processing_status.pop(store_key, None)
        
        return {
            "message": "Document deleted successfully",
            "document_id": document_id
        }


# Singleton instance
document_service = DocumentService()

