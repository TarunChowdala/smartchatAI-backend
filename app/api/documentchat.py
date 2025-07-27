from fastapi import APIRouter, UploadFile, File, HTTPException, Request, BackgroundTasks
from pydantic import BaseModel, Field
# from typing import  List, Any
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_community.document_loaders import (
    PyPDFLoader, TextLoader, Docx2txtLoader,
    UnstructuredPowerPointLoader, UnstructuredExcelLoader
)
from langchain.text_splitter import RecursiveCharacterTextSplitter
# from langchain.llms.base import LLM
# from langchain.chains import RetrievalQA
import requests
import os
from pathlib import Path
from app.api.auth import verify_token
from dotenv import load_dotenv
import uuid

load_dotenv()
router = APIRouter()

# global variables to handle multiple users states
vectorstores = {}
qa_chains = {}
processing_status = {}

# constants
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
SUPPORTED_EXTENSIONS = {
    '.pdf': PyPDFLoader, '.txt': TextLoader, '.docx': Docx2txtLoader,
    '.doc': Docx2txtLoader, '.ppt': UnstructuredPowerPointLoader,
    '.pptx': UnstructuredPowerPointLoader, '.xls': UnstructuredExcelLoader,
    '.xlsx': UnstructuredExcelLoader
}

# Models
class QueryRequest(BaseModel):
    question: str
    task_id: str

def get_document_loader(file_path: str):
    file_extension = Path(file_path).suffix.lower()
    if file_extension not in SUPPORTED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type. Supported types are: {', '.join(SUPPORTED_EXTENSIONS.keys())}"
        )
    return SUPPORTED_EXTENSIONS[file_extension](file_path)

def process_document(task_id: str, file_path: str):
    try:
        loader = get_document_loader(file_path)
        documents = loader.load()
        if not documents:
            raise Exception("No content could be extracted from the document")

        splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
        texts = splitter.split_documents(documents)

        embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
        vectorstore = FAISS.from_documents(texts, embeddings)

        vectorstores[task_id] = vectorstore

    except Exception as e:
        print(f"[Error processing doc]: {e}")
    finally:
        processing_status[task_id] = False
        if os.path.exists(file_path):
            os.remove(file_path)


@router.post("/upload")
async def upload_document(file: UploadFile = File(...), request: Request = None, background_tasks: BackgroundTasks = None):
    verify_token(request)

    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")

    file_extension = Path(file.filename).suffix.lower()
    if file_extension not in SUPPORTED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type. Supported types are: {', '.join(SUPPORTED_EXTENSIONS.keys())}"
        )

    task_id = str(uuid.uuid4())
    processing_status[task_id] = True

    file_location = f"temp_docs/{task_id}_{file.filename}"
    os.makedirs("temp_docs", exist_ok=True)

    with open(file_location, "wb") as f:
        content = await file.read()
        if not content:
            raise HTTPException(status_code=400, detail="Empty file uploaded")
        f.write(content)

    background_tasks.add_task(process_document, task_id, file_location)

    return {"message": "File uploaded successfully. Processing in background...", "task_id": task_id}

@router.get("/status")
def get_status(request: Request, task_id: str):
    verify_token(request)
    if task_id not in processing_status:
        raise HTTPException(status_code=404, detail="Invalid task_id")
    return {"processing": processing_status[task_id], "ready": not processing_status[task_id] and task_id in qa_chains}

@router.post("/ask")
async def ask_question(req: QueryRequest, request: Request):
    verify_token(request)

    task_id = req.task_id

    if processing_status.get(task_id):
        raise HTTPException(status_code=400, detail="Still processing document. Please wait.")

    try:
        question = req.question

        vector_store = vectorstores.get(task_id)
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

        answer = call_gemini_llm(prompt, api_key=GEMINI_API_KEY)

        return {"question": question, "answer": answer}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def call_gemini_llm(prompt: str, api_key: str, model_name: str = "gemini-2.5-flash") -> str:
    headers = {
        "x-goog-api-key": api_key,
        "Content-Type": "application/json"
    }
    json_body = {
        "contents": [
            {"parts": [{"text": prompt}]}
        ]
    }

    try:
        response = requests.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent",
            headers=headers, json=json_body, timeout=30
        )
        response.raise_for_status()
        data = response.json()
        return data["candidates"][0]["content"]["parts"][0]["text"]
    except Exception as e:
        print("Gemini LLM error:", e)
        return "Error: Could not get response from Gemini"