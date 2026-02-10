"""Security utilities for authentication and authorization."""
import base64
import os
from fastapi import HTTPException, Request
from firebase_admin import auth
from cryptography.fernet import Fernet
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


def _get_fernet() -> Fernet:
    """
    Get Fernet cipher instance for encryption/decryption.
    
    Returns:
        Fernet cipher instance
        
    Raises:
        ValueError: If encryption key is not configured
    """
    encryption_key = settings.encryption_key
    
    if not encryption_key:
        # Generate a key if not set (for development only - should be set in production)
        # In production, set ENCRYPTION_KEY in environment variables
        raise ValueError(
            "ENCRYPTION_KEY not set. Generate one with: python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'"
        )
    
    try:
        return Fernet(encryption_key.encode())
    except Exception as e:
        raise ValueError(f"Invalid encryption key format: {str(e)}")


def encrypt_api_key(api_key: str) -> str:
    """
    Encrypt API key before storing in database.
    
    Args:
        api_key: Plain text API key
        
    Returns:
        Encrypted API key string
        
    Raises:
        ValueError: If encryption fails or key not configured
    """
    if not api_key:
        return api_key
    
    try:
        fernet = _get_fernet()
        encrypted = fernet.encrypt(api_key.encode())
        return encrypted.decode()
    except ValueError:
        raise
    except Exception as e:
        raise ValueError(f"Failed to encrypt API key: {str(e)}")


def decrypt_api_key(encrypted_api_key: str) -> str:
    """
    Decrypt API key retrieved from database.
    
    Args:
        encrypted_api_key: Encrypted API key string
        
    Returns:
        Decrypted API key string
        
    Raises:
        ValueError: If decryption fails or key not configured
    """
    if not encrypted_api_key:
        return encrypted_api_key
    
    try:
        fernet = _get_fernet()
        decrypted = fernet.decrypt(encrypted_api_key.encode())
        return decrypted.decode()
    except ValueError:
        raise
    except Exception as e:
        # If decryption fails, try returning as-is (for backward compatibility with unencrypted keys)
        # This allows migration of existing keys
        return encrypted_api_key

