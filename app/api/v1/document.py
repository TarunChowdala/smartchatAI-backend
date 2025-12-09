"""Document chat API routes."""
from fastapi import APIRouter, UploadFile, File, Depends, BackgroundTasks
from app.dependencies import get_current_user
from app.services.document_service import document_service
from app.models.schemas import QueryRequest, QueryResponse, UploadResponse, StatusResponse
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
    
    Args:
        file: Document file to upload
        background_tasks: FastAPI background tasks
        current_user: Current user data from token (dependency injection)
        
    Returns:
        Upload response with task_id
    """
    content = await file.read()
    result = document_service.upload_document(
        file_content=content,
        filename=file.filename,
        background_tasks=background_tasks
    )
    return result


@router.get("/status", response_model=StatusResponse)
@handle_exceptions
async def get_status(
    task_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Get document processing status.
    
    Args:
        task_id: Task identifier
        current_user: Current user data from token (dependency injection)
        
    Returns:
        Processing status response
    """
    return document_service.get_status(task_id)


@router.post("/ask", response_model=QueryResponse)
@handle_exceptions
async def ask_question(
    req: QueryRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Ask question about uploaded document.
    
    Args:
        req: Query request with question and task_id
        current_user: Current user data from token (dependency injection)
        
    Returns:
        Question and answer response
    """
    return document_service.ask_question(req.question, req.task_id)

