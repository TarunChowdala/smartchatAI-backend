"""Help and Support API routes."""
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, HTTPException
from app.dependencies import get_current_user
from app.services.help_service import help_service
from app.models.schemas import HelpQueryRequest, HelpReplyRequest, HelpStatusRequest
from app.decorators import handle_exceptions

router = APIRouter(prefix="/help", tags=["Help & Support"])


@router.post("/queries")
@handle_exceptions
async def submit_query(
    data: HelpQueryRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Submit a new help/support query.
    """
    user_id = current_user["uid"]
    return help_service.submit_query(user_id, data.subject, data.message)


@router.get("/queries")
@handle_exceptions
async def get_my_queries(current_user: dict = Depends(get_current_user)):
    """
    Get all help queries submitted by the current user.
    """
    user_id = current_user["uid"]
    return help_service.get_user_queries(user_id)


@router.get("/queries/all")
@handle_exceptions
async def get_all_queries(
    status: Optional[str] = Query(None, description="Filter by status (open, in_progress, resolved, closed)"),
    current_user: dict = Depends(get_current_user)
):
    """
    Get all help queries (Admin only).
    """
    admin_id = current_user["uid"]
    return help_service.get_all_queries(admin_id, status)


@router.post("/queries/{query_id}/reply")
@handle_exceptions
async def reply_to_query(
    query_id: str,
    data: HelpReplyRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Reply to a help query (Admin only).
    """
    admin_id = current_user["uid"]
    return help_service.reply_to_query(admin_id, query_id, data.reply)


@router.patch("/queries/{query_id}/status")
@handle_exceptions
async def update_query_status(
    query_id: str,
    data: HelpStatusRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Update the status of a help query (Admin only).
    """
    admin_id = current_user["uid"]
    return help_service.update_status(admin_id, query_id, data.status)

