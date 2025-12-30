"""Document chat API routes with RAG support."""
from fastapi import APIRouter, UploadFile, File, Depends, BackgroundTasks
from app.dependencies import get_current_user
from app.services.document_service import document_service
from app.models.schemas import QueryRequest, QueryResponse, UploadResponse, ChatRequest, ChatResponse, DeleteResponse
from app.decorators import handle_exceptions

router = APIRouter(prefix="/document", tags=["Document Chat"])


@router.post("/upload", response_model=UploadResponse)
@handle_exceptions
async def upload_document(
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    current_user: dict = Depends(get_current_user)
):
    """
    Upload document for Q&A processing.
    
    User ID is extracted from Firebase token, never from request body.
    Stores metadata in Firestore and processes in background.
    
    Args:
        file: Document file to upload
        background_tasks: FastAPI background tasks
        current_user: Current user data from token (dependency injection)
        
    Returns:
        Upload response with document_id
    """
    # Extract user_id from token (never from request)
    user_id = current_user["uid"]
    
    content = await file.read()
    result = document_service.upload_document(
        file_content=content,
        filename=file.filename or "unknown",
        user_id=user_id,
        background_tasks=background_tasks
    )
    return result


@router.get("/{document_id}/status")
@handle_exceptions
async def get_document_status(
    document_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Check document processing status.
    
    Returns status, filename, chunks count, and any errors.
    User can only check their own documents.
    """
    user_id = current_user["uid"]
    return document_service.get_status(document_id, user_id)


@router.delete("/{document_id}", response_model=DeleteResponse)
@handle_exceptions
async def delete_document(
    document_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Delete a document.
    
    Removes document from Firestore and clears vectorstore from RAM.
    User can only delete their own documents.
    """
    user_id = current_user["uid"]
    return document_service.delete_document(document_id, user_id)


@router.post("/ask", response_model=QueryResponse)
@handle_exceptions
async def ask_question(
    req: QueryRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Ask question about uploaded document using RAG.
    
    Uses advanced retrieval (MMR) and filters by user_id from token.
    
    Args:
        req: Query request with question and task_id (document_id)
        current_user: Current user data from token (dependency injection)
        
    Returns:
        Question and answer response
    """
    user_id = current_user["uid"]
    return document_service.ask_question(
        question=req.question,
        document_id=req.task_id,
        user_id=user_id,
        use_mmr=True,
        k=5
    )


@router.post("/chat", response_model=ChatResponse)
@handle_exceptions
async def chat(
    req: ChatRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Chat with documents using advanced RAG.
    
    - Uses MMR retrieval for better diversity
    - Filters by user_id (from token)
    - Optionally filters by document_id
    - Returns answer with source documents
    
    User ID is extracted from Firebase token, never from request body.
    """
    user_id = current_user["uid"]
    
    # Use document_id from request if provided, otherwise use task_id for backward compatibility
    document_id = req.document_id if req.document_id else req.task_id
    
    result = document_service.ask_question(
        question=req.question,
        document_id=document_id,
        user_id=user_id,
        use_mmr=req.use_mmr,
        k=req.k
    )
    
    return result


@router.post("/cleanup")
@handle_exceptions
async def cleanup_orphaned_vectorstores(
    current_user: dict = Depends(get_current_user)
):
    """
    Clean up orphaned vectorstores (vectorstores without corresponding documents).
    
    This helps free up disk space by removing vectorstores for deleted documents.
    Only accessible to authenticated users.
    """
    result = document_service.cleanup_orphaned_vectorstores()
    return result

