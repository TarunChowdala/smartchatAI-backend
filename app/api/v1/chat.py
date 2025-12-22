"""Chat API routes."""
from fastapi import APIRouter, Depends, Query
from app.dependencies import get_current_user
from app.services.chat_service import chat_service
from app.models.schemas import MessageInput, MessageResponse, SessionResponse, MessagesResponse, DeleteResponse, SessionsListResponse
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


@router.get("/sessions", response_model=SessionsListResponse)
@handle_exceptions
async def get_all_sessions(
    limit: int = Query(50, ge=1, le=200, description="Maximum number of sessions to return"),
    current_user: dict = Depends(get_current_user)
):
    """
    Get all sessions for the current user.
    
    Returns list of sessions with metadata including message count.
    Ordered by most recently updated first.
    """
    user_id = current_user["uid"]
    return chat_service.get_all_sessions(user_id, limit)


@router.get("/sessions/{session_id}", response_model=SessionResponse)
@handle_exceptions
async def get_session(
    session_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Get session information.
    
    Returns session metadata including message count.
    User can only access their own sessions.
    """
    user_id = current_user["uid"]
    return chat_service.get_session(session_id, user_id)


@router.get("/sessions/{session_id}/messages", response_model=MessagesResponse)
@handle_exceptions
async def get_messages(
    session_id: str,
    limit: int = Query(50, ge=1, le=200, description="Maximum number of messages to return"),
    current_user: dict = Depends(get_current_user)
):
    """
    Get messages for a session.
    
    Returns all messages in the session ordered by timestamp.
    User can only access their own sessions.
    """
    user_id = current_user["uid"]
    return chat_service.get_messages(session_id, user_id, limit)


@router.delete("/sessions/{session_id}", response_model=DeleteResponse)
@handle_exceptions
async def delete_session(
    session_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Delete a chat session.
    
    Removes session and all its messages from Firestore.
    User can only delete their own sessions.
    """
    user_id = current_user["uid"]
    return chat_service.delete_session(session_id, user_id)

