"""Document processing service for RAG operations."""
import os
import uuid
from pathlib import Path
from typing import Optional
from fastapi import HTTPException, BackgroundTasks
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_community.document_loaders import (
    PyPDFLoader,
    TextLoader,
    Docx2txtLoader,
    UnstructuredPowerPointLoader,
    UnstructuredExcelLoader
)
from langchain.text_splitter import RecursiveCharacterTextSplitter
import requests
from app.config import settings


class DocumentService:
    """Service for document processing and Q&A."""
    
    def __init__(self):
        self.api_key = settings.gemini_api_key
        self.model = settings.gemini_model
        self.api_url = settings.gemini_api_url
        self.temp_dir = settings.temp_docs_dir
        
        # In-memory storage (consider Redis/DB for production)
        self.vectorstores: dict[str, FAISS] = {}
        self.processing_status: dict[str, bool] = {}
        
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
    
    def process_document(self, task_id: str, file_path: str) -> None:
        """
        Process document in background: load, split, and create vector store.
        
        Args:
            task_id: Unique task identifier
            file_path: Path to document file
        """
        try:
            loader = self.get_document_loader(file_path)
            documents = loader.load()
            
            if not documents:
                raise Exception("No content could be extracted from the document")
            
            splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
            texts = splitter.split_documents(documents)
            
            embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
            vectorstore = FAISS.from_documents(texts, embeddings)
            
            self.vectorstores[task_id] = vectorstore
            
        except Exception as e:
            print(f"[Error processing doc]: {e}")
        finally:
            self.processing_status[task_id] = False
            if os.path.exists(file_path):
                os.remove(file_path)
    
    def upload_document(self, file_content: bytes, filename: str, background_tasks: BackgroundTasks) -> dict:
        """
        Upload and process document.
        
        Args:
            file_content: File content bytes
            filename: Original filename
            background_tasks: FastAPI background tasks
            
        Returns:
            Upload response with task_id
            
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
        
        task_id = str(uuid.uuid4())
        self.processing_status[task_id] = True
        
        os.makedirs(self.temp_dir, exist_ok=True)
        file_location = f"{self.temp_dir}/{task_id}_{filename}"
        
        with open(file_location, "wb") as f:
            f.write(file_content)
        
        background_tasks.add_task(self.process_document, task_id, file_location)
        
        return {
            "message": "File uploaded successfully. Processing in background...",
            "task_id": task_id
        }
    
    def get_status(self, task_id: str) -> dict:
        """
        Get processing status for a task.
        
        Args:
            task_id: Task identifier
            
        Returns:
            Status response
            
        Raises:
            HTTPException: If task_id is invalid
        """
        if task_id not in self.processing_status:
            raise HTTPException(status_code=404, detail="Invalid task_id")
        
        return {
            "processing": self.processing_status[task_id],
            "ready": not self.processing_status[task_id] and task_id in self.vectorstores
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
    
    def ask_question(self, question: str, task_id: str) -> dict:
        """
        Ask question about uploaded document.
        
        Args:
            question: User question
            task_id: Task identifier
            
        Returns:
            Question and answer response
            
        Raises:
            HTTPException: If document is still processing or task_id is invalid
        """
        if self.processing_status.get(task_id):
            raise HTTPException(
                status_code=400,
                detail="Still processing document. Please wait."
            )
        
        vector_store = self.vectorstores.get(task_id)
        if not vector_store:
            raise HTTPException(status_code=404, detail="Invalid or expired task_id")
        
        docs = vector_store.similarity_search(question, k=3)
        context = "\n\n".join([doc.page_content for doc in docs])
        
        prompt = f"""
        You are a knowledgeable and precise assistant helping the user understand information **only** from the context provided below.

        You must follow these rules:
        - ONLY use the context below to answer the question.
        - If the context does not contain the answer, say: "Apologies, I couldn't locate an answer to your question within the current context. However, feel free to ask any question related to the content — I'm here to assist you."
        - Do NOT hallucinate or invent any information not present in the context.
        - Answer concisely, clearly, and professionally.
        - Do not reference external sources or general knowledge.

        ---

        Context:
        {context}

        ---

        Question: {question}

        Answer:
        """
        
        answer = self.call_gemini_llm(prompt)
        
        return {"question": question, "answer": answer}


# Singleton instance
document_service = DocumentService()

