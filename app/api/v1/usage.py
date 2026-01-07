"""Usage and Admin API routes."""
from fastapi import APIRouter, Depends, Query, HTTPException
from app.dependencies import get_current_user
from app.services.usage_limit_service import usage_limit_service
from app.decorators import handle_exceptions

router = APIRouter(prefix="/usage", tags=["Usage & Admin"])


@router.get("/my-usage")
@handle_exceptions
async def get_my_usage(current_user: dict = Depends(get_current_user)):
    """
    Get current user's usage statistics and limits.
    """
    user_id = current_user["uid"]
    return usage_limit_service.get_user_usage(user_id)


@router.get("/user-usage/{target_user_id}")
@handle_exceptions
async def get_user_usage(
    target_user_id: str, 
    current_user: dict = Depends(get_current_user)
):
    """
    Get any user's usage statistics (Admin only).
    """
    admin_id = current_user["uid"]
    if not usage_limit_service.is_admin(admin_id):
        raise HTTPException(status_code=403, detail="Admin access required")
    
    return usage_limit_service.get_user_usage(target_user_id)


@router.post("/reset/{target_user_id}")
@handle_exceptions
async def reset_user_usage(
    target_user_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Reset usage limits for a specific user (Admin only).
    """
    admin_id = current_user["uid"]
    return usage_limit_service.reset_usage(target_user_id, admin_id)


@router.get("/all-users")
@handle_exceptions
async def list_all_users_usage(
    limit: int = Query(100, ge=1, le=1000),
    current_user: dict = Depends(get_current_user)
):
    """
    List all users and their usage statistics (Admin only).
    """
    admin_id = current_user["uid"]
    return usage_limit_service.list_all_users_usage(admin_id, limit)

