"""Chat API routes."""
from fastapi import APIRouter, Depends
from app.dependencies import get_current_user
from app.services.chat_service import chat_service
from app.models.schemas import MessageInput, MessageResponse
from app.decorators import handle_exceptions

router = APIRouter(prefix="/chat", tags=["Chat"])


@router.post("/send-message", response_model=MessageResponse)
@handle_exceptions
async def send_message(
    data: MessageInput,
    current_user: dict = Depends(get_current_user)
):
    """
    Send chat message and get AI response.
    
    Args:
        data: Message input data
        current_user: Current user data from token (dependency injection)
        
    Returns:
        AI response message
    """
    reply = chat_service.send_message(
        user_id=data.user_id,
        message=data.message,
        session_id=data.session_id
    )
    return {"reply": reply}

