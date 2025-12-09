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
    if settings.google_application_credentials_json:
        import json
        # Parse JSON string if needed
        try:
            cred_data = json.loads(settings.google_application_credentials_json)
        except (json.JSONDecodeError, TypeError):
            # If it's already a dict or invalid, use as is
            cred_data = settings.google_application_credentials_json
        cred = credentials.Certificate(cred_data)
    else:
        service_account_path = settings.google_application_credentials_path
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
