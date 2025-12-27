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
    # Read JSON from settings (which reads from env)
    service_account_json_str = settings.google_application_credentials_json
    
    if service_account_json_str:
        try:
            cred_info = json.loads(service_account_json_str)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in GOOGLE_APPLICATION_CREDENTIALS_JSON: {e}")
        
        cred = service_account.Credentials.from_service_account_info(cred_info)
    else:
      raise ValueError("GOOGLE_APPLICATION_CREDENTIALS_JSON environment variable is not set")
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
