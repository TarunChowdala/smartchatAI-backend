from fastapi import APIRouter, UploadFile, File, HTTPException, Request
from pydantic import BaseModel, Field
from typing import Optional, List, Mapping, Any
from langchain_huggingface import HuggingFaceEmbeddings
from langchain.vectorstores import FAISS
from langchain_community.document_loaders import (
    PyPDFLoader,
    TextLoader,
    Docx2txtLoader,
    UnstructuredPowerPointLoader,
    UnstructuredExcelLoader
)
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.llms.base import LLM
from langchain.chains import RetrievalQA
import requests
import os
from pathlib import Path
from app.api.auth import verify_token

router = APIRouter()

# Global variables
vectorstore = None
qa_chain = None

# OpenRouter configuration
OPENROUTER_API_KEY = "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"
OPENROUTER_MODEL_NAME = "mistralai/mistral-7b-instruct:free"

# Supported file extensions and their corresponding loaders
SUPPORTED_EXTENSIONS = {
    '.pdf': PyPDFLoader,
    '.txt': TextLoader,
    '.docx': Docx2txtLoader,
    '.doc': Docx2txtLoader,
    '.ppt': UnstructuredPowerPointLoader,
    '.pptx': UnstructuredPowerPointLoader,
    '.xls': UnstructuredExcelLoader,
    '.xlsx': UnstructuredExcelLoader
}


class QueryRequest(BaseModel):
    question: str


class OpenRouterLLM(LLM):
    api_key: str = Field(default=OPENROUTER_API_KEY)
    model_name: str = Field(default=OPENROUTER_MODEL_NAME)

    def _call(self, prompt: str, stop: Optional[List[str]] = None) -> str:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        messages = [
            {
                "role": "system",
                "content": "You are a friendly and helpful AI assistant. Your primary goal is to engage in natural, human-like conversation.\n\nWhen users greet you:\n- Simply respond to the greeting naturally\n- Don't mention document capabilities unless specifically asked\n- Keep the response casual and friendly\n\nWhen users ask about your capabilities:\n- Explain that you're an AI assistant that can help with various tasks\n- Only mention document analysis if they specifically ask about it\n- Keep the explanation simple and conversational\n\nWhen users ask about documents:\n- Provide clear, accurate answers based on the document content\n- If information isn't available, explain what you do know\n- If the question is unclear, ask for clarification\n- Keep responses concise and helpful\n\nAlways maintain a warm, friendly tone and respond naturally to the conversation flow.",
            },
            {"role": "user", "content": prompt}
        ]   

        json_data = {
            "model": self.model_name,
            "messages": messages,
            "max_tokens": 512,
            "temperature": 0.3,
            "stop": stop,
        }

        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            json=json_data,
            timeout=30,
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]

    @property
    def _identifying_params(self) -> Mapping[str, Any]:
        return {"model_name": self.model_name}

    @property
    def _llm_type(self) -> str:
        return "openrouter"


def get_document_loader(file_path: str):
    """Get the appropriate document loader based on file extension."""
    file_extension = Path(file_path).suffix.lower()
    if file_extension not in SUPPORTED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type. Supported types are: {', '.join(SUPPORTED_EXTENSIONS.keys())}"
        )
    return SUPPORTED_EXTENSIONS[file_extension](file_path)


@router.post("/upload")
async def upload_document(file: UploadFile = File(...), request: Request = None):
    # Verify token
    verify_token(request)
    
    global vectorstore, qa_chain

    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")

    file_extension = Path(file.filename).suffix.lower()
    if file_extension not in SUPPORTED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type. Supported types are: {', '.join(SUPPORTED_EXTENSIONS.keys())}"
        )

    file_location = f"temp_docs/{file.filename}"
    os.makedirs("temp_docs", exist_ok=True)
    
    try:
        # Save the uploaded file
        with open(file_location, "wb") as f:
            content = await file.read()
            if not content:
                raise HTTPException(status_code=400, detail="Empty file uploaded")
            f.write(content)

        # Process document
        try:
            loader = get_document_loader(file_location)
            documents = loader.load()
        except Exception as e:
            raise HTTPException(
                status_code=400,
                detail=f"Error loading document: {str(e)}"
            )

        if not documents:
            raise HTTPException(status_code=400, detail="No content could be extracted from the document")

        # Split and process the content
        splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
        texts = splitter.split_documents(documents)

        # Setup vector store and QA chain
        embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
        vectorstore = FAISS.from_documents(texts, embeddings)
        llm = OpenRouterLLM()
        qa_chain = RetrievalQA.from_chain_type(llm=llm, retriever=vectorstore.as_retriever())

        return {"message": "Document uploaded and processed successfully."}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing document: {str(e)}")
    finally:
        # Clean up the temporary file
        if os.path.exists(file_location):
            os.remove(file_location)


@router.post("/ask")
async def ask_question(req: QueryRequest, request: Request):
    # Verify token
    verify_token(request)
    
    if not qa_chain:
        raise HTTPException(status_code=400, detail="Please upload a document first.")
    
    try:
        # Use invoke instead of run
        answer = qa_chain.invoke({"query": req.question})
        return {"question": req.question, "answer": answer["result"]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing question: {str(e)}")
