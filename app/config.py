from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Firebase Configuration
    firebase_api_key: str = ""
    google_application_credentials_json: Optional[str] = None
    
    # Gemini AI Configuration
    gemini_api_key: str = ""
    
    # Application Configuration
    app_name: str = "SmartChatAI Backend"
    app_version: str = "1.0.0"
    debug: bool = False
    
    # CORS Configuration
    cors_origins: list[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
        "https://smartchataiapp.vercel.app",
    ]
    
    # File Upload Configuration
    max_upload_size: int = 10 * 1024 * 1024  # 10MB
    temp_docs_dir: str = "temp_docs"
    temp_resumes_dir: str = "temp_resumes"
    vectorstores_dir: str = "vectorstores"  # Directory for persistent FAISS vectorstores
    
    # Gemini Model Configuration
    gemini_model: str = "gemini-2.5-flash"
    gemini_api_url: str = "https://generativelanguage.googleapis.com/v1beta/models"
    
    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
