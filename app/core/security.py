"""Security utilities for authentication and authorization."""
import base64
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


def decrypt_password(encrypted_password: str) -> str:
    """
    Decode base64 encoded password received from frontend.
    
    Args:
        encrypted_password: Base64 encoded password string
        
    Returns:
        Decoded password string
        
    Raises:
        ValueError: If base64 decoding fails
    """
    if not encrypted_password:
        return encrypted_password
    
    try:
        # Decode base64 password
        decoded_bytes = base64.b64decode(encrypted_password)
        decoded_password = decoded_bytes.decode('utf-8')
        return decoded_password
    except Exception as e:
        # If base64 decode fails, return as-is (for backward compatibility)
        # This allows plain passwords to still work during transition
        return encrypted_password

