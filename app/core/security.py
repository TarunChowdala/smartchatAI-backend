"""Security utilities for authentication and authorization."""
from fastapi import HTTPException, Request
from firebase_admin import auth
from app.config import settings


def verify_firebase_token(request: Request) -> dict:
    """
    Verify Firebase ID token from Authorization header.
    
    Args:
        request: FastAPI Request object
        
    Returns:
        Decoded token dictionary with user info
        
    Raises:
        HTTPException: If token is invalid or missing
    """
    auth_header = request.headers.get("Authorization")
    
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail="No valid authorization header"
        )
    
    id_token = auth_header.split("Bearer ")[1]
    
    try:
        decoded_token = auth.verify_id_token(id_token)
        return decoded_token
    except Exception as e:
        raise HTTPException(
            status_code=401,
            detail=f"Authentication failed: {str(e)}"
        )


def get_current_user_uid(request: Request) -> str:
    """
    Extract user UID from verified Firebase token.
    
    Args:
        request: FastAPI Request object
        
    Returns:
        User UID string
    """
    decoded_token = verify_firebase_token(request)
    return decoded_token["uid"]

