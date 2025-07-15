from fastapi import APIRouter, UploadFile, File, HTTPException, Request
from pydantic import BaseModel, Field
from typing import Optional, List, Mapping, Any
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
from langchain.llms.base import LLM
from langchain.chains import RetrievalQA
import requests
import os
from pathlib import Path
from app.api.auth import verify_token
from dotenv import load_dotenv
load_dotenv()

router = APIRouter()

# Global variables
vectorstore = None
qa_chain = None

# OpenRouter configuration
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL_NAME = "gemini-2.5-flash:generateContent"

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


class GeminiLLM(LLM):
    api_key: str = Field(default=GEMINI_API_KEY)
    model_name: str = Field(default="gemini-2.5-flash")

    def _call(self, prompt: str, stop: Optional[List[str]] = None) -> str:
        headers = {
            "x-goog-api-key": self.api_key,
            "Content-Type": "application/json"
        }

        # instructions = (
        #     "You are a professional and friendly AI assistant. "
        #     "Respond clearly, helpfully, and respectfully, using simple language. "
        #     "Use only the provided context to answer questions—if not found, say so politely. "
        #     "Avoid emojis and do not guess. Stay warm and welcoming throughout.\n\n"
        # )

        full_prompt =  prompt

        json_body = {
            "contents": [
                {"parts": [{"text": full_prompt}]}
            ]
        }
        response = requests.post(
            "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent",
            headers=headers,
            json=json_body,
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()
        try:
            return data["candidates"][0]["content"]["parts"][0]["text"]
        except Exception:
            return "Error: Unexpected Gemini API response format"

    @property
    def _identifying_params(self) -> Mapping[str, Any]:
        return {"model_name": self.model_name}

    @property
    def _llm_type(self) -> str:
        return "gemini"


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
        llm = GeminiLLM()
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
