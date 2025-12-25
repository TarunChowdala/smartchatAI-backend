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
    # Write service account JSON from environment variable to a file (for Render)
    service_account_json = settings.google_application_credentials_json
    
    if service_account_json:
        service_account_path = "/tmp/firebase-adminsdk.json"
        
        # Handle both string and dict formats
        if isinstance(service_account_json, str):
            json_content = service_account_json
        else:
            # It's a dict, convert to JSON string
            json_content = json.dumps(service_account_json)
        
        with open(service_account_path, "w") as f:
            f.write(json_content)
    else:
        service_account_path = settings.google_application_credentials_path
    
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
