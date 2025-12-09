"""Authentication API routes."""
from fastapi import APIRouter, Depends, Request
from app.dependencies import get_current_user, get_current_user_id
from app.services.auth_service import auth_service
from app.models.schemas import (
    LoginRequest,
    SignupRequest,
    GoogleSignupRequest,
    UpdateProfileRequest,
    UpdatePasswordRequest,
)
from app.decorators import handle_exceptions

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/login")
@handle_exceptions
async def login_user(data: LoginRequest):
    """
    Authenticate user with email and password.
    
    Returns:
        Login response with tokens and user info
    """
    return auth_service.login(data)


@router.post("/signup")
@handle_exceptions
async def signup_user(data: SignupRequest):
    """
    Create new user account.
    
    Returns:
        Signup response with user info
    """
    return auth_service.signup(data)


@router.post("/google-signup")
@handle_exceptions
async def google_signup(data: GoogleSignupRequest):
    """
    Create new user account via Google OAuth.
    
    Returns:
        Signup response with user info
    """
    return auth_service.google_signup(data)


@router.get("/me")
@handle_exceptions
async def get_logged_in_user(current_user: dict = Depends(get_current_user)):
    """
    Get current authenticated user data.
    
    Args:
        current_user: Current user data from token (dependency injection)
        
    Returns:
        User data dictionary
    """
    uid = current_user["uid"]
    return auth_service.get_user(uid)


@router.post("/update-me")
@handle_exceptions
async def update_profile(
    update_data: UpdateProfileRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Update current user's profile.
    
    Args:
        update_data: Profile update data
        current_user: Current user data from token (dependency injection)
        
    Returns:
        Updated user data
    """
    uid = current_user["uid"]
    return auth_service.update_profile(update_data.email, update_data, uid)


@router.post("/update-password")
@handle_exceptions
async def update_password(data: UpdatePasswordRequest):
    """
    Update user password.
    
    Args:
        data: Update password request data
        
    Returns:
        New tokens after password update
    """
    return auth_service.update_password(data)

