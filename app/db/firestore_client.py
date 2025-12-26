"""Firestore database client initialization."""
import os
import json
from google.cloud import firestore
from google.oauth2 import service_account
from app.config import settings


def get_firestore_db() -> firestore.Client:
    """
    Get Firestore database client instance.
    
    Returns:
        Firestore Client instance
    """
    # Read JSON directly from environment variable (bypass pydantic)
    service_account_json_str = os.getenv("GOOGLE_APPLICATION_CREDENTIALS_JSON")
    
    if service_account_json_str:
        try:
            cred_info = json.loads(service_account_json_str)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in GOOGLE_APPLICATION_CREDENTIALS_JSON: {e}")
        
        cred = service_account.Credentials.from_service_account_info(cred_info)
    else:
        # Fall back to file path - use hardcoded default to avoid pydantic corruption
        default_path = "app/config/smartchatai-firebase-adminsdk.json"
        
        # Try settings first, but validate it's not corrupted
        service_account_path = settings.google_application_credentials_path
        
        # If path looks corrupted (JSON), use default
        if not isinstance(service_account_path, str) or service_account_path.startswith('{') or len(service_account_path) > 500:
            service_account_path = default_path
        
        if not os.path.exists(service_account_path):
            raise FileNotFoundError(
                f"Firebase credentials file not found at {service_account_path}. "
                f"Set GOOGLE_APPLICATION_CREDENTIALS_JSON environment variable or ensure file exists."
            )
        
        cred = service_account.Credentials.from_service_account_file(service_account_path)
    
    return firestore.Client(credentials=cred)


# Global db instance (for backward compatibility during migration)
_db_instance = None


def get_db_instance() -> firestore.Client:
    """Get or create global db instance."""
    global _db_instance
    if _db_instance is None:
        _db_instance = get_firestore_db()
    return _db_instance


# Export db for backward compatibility
db = get_db_instance()
