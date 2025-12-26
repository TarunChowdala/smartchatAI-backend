"""Main FastAPI application."""
import os
import firebase_admin
from firebase_admin import credentials
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.api.v1 import auth, chat, document, resume

# Initialize Firebase Admin SDK
if not firebase_admin._apps:
    import json
    
    # Read JSON directly from environment variable (bypass pydantic)
    service_account_json_str = os.getenv("GOOGLE_APPLICATION_CREDENTIALS_JSON")
    
    if service_account_json_str:
        try:
            # Parse JSON string to dict
            cred_data = json.loads(service_account_json_str)
            cred = credentials.Certificate(cred_data)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in GOOGLE_APPLICATION_CREDENTIALS_JSON: {e}")
    else:
        # Fall back to file path
        default_path = "app/config/smartchatai-firebase-adminsdk.json"
        service_account_path = settings.google_application_credentials_path
        
        # If path looks corrupted (JSON), use default
        if not isinstance(service_account_path, str) or service_account_path.startswith('{') or len(service_account_path) > 500:
            service_account_path = default_path
        
        if os.path.exists(service_account_path):
            cred = credentials.Certificate(service_account_path)
        else:
            # Don't raise error here - let it fail gracefully if credentials are needed
            cred = None
    
    if cred:
        firebase_admin.initialize_app(cred)

# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    debug=settings.debug
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=3600,
)

# Include routers
app.include_router(auth.router)
app.include_router(chat.router)
app.include_router(document.router)
app.include_router(resume.router)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "SmartChatAI Backend API",
        "version": settings.app_version,
        "status": "running"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}
