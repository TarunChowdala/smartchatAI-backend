import os
import firebase_admin
from firebase_admin import credentials

# Write service account JSON from environment variable to a file (for Render)
service_account_json = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS_JSON")
if service_account_json:
    with open("/tmp/firebase-adminsdk.json", "w") as f:
        f.write(service_account_json)
    service_account_path = "/tmp/firebase-adminsdk.json"
else:
    service_account_path = "config/smartchatai-firebase-adminsdk.json"  # fallback for local dev

if not firebase_admin._apps:
    cred = credentials.Certificate(service_account_path)
    firebase_admin.initialize_app(cred)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import chat
from app.api.documentchat import router as documentchat_router
from app.api.auth import router as auth_router
from app.api.resumeanalyser import router as resume_analyser

app = FastAPI()

# Configure CORS
origins = [
    "http://localhost:3000",     # React default port
    "http://localhost:5173",     # Vite default port
    "http://127.0.0.1:3000",    # React alternative
    "http://127.0.0.1:5173",    # Vite alternative
    "http://localhost:8000",     # FastAPI default
    "http://127.0.0.1:8000",    # FastAPI alternative
    "http://localhost:8080",     # Common development port
    "http://127.0.0.1:8080",    # Common development port
]

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=3600,
)

app.include_router(chat.router, prefix="/chat")
app.include_router(documentchat_router, prefix="/document")
app.include_router(auth_router, prefix="/auth")
app.include_router(resume_analyser, prefix="/resume")
