"""Pydantic schemas for API requests and responses."""
from pydantic import BaseModel, EmailStr, Field
from typing import Optional


# Auth Schemas
class LoginRequest(BaseModel):
    """Login request schema."""
    email: EmailStr
    password: str


class SignupRequest(BaseModel):
    """Signup request schema."""
    email: EmailStr
    password: str
    name: str
    uid: str
    id_token: str = Field(alias="idToken")
    about: Optional[str] = None


class GoogleSignupRequest(BaseModel):
    """Google OAuth signup request schema."""
    email: EmailStr
    name: str
    uid: str
    id_token: str = Field(alias="idToken")
    profile_image: str = Field(alias="profileImage")


class UpdateProfileRequest(BaseModel):
    """Update profile request schema."""
    email: EmailStr
    name: Optional[str] = None
    about: Optional[str] = None


class UpdatePasswordRequest(BaseModel):
    """Update password request schema."""
    email: EmailStr
    current_password: str
    new_password: str


class RefreshTokenRequest(BaseModel):
    """Refresh token request schema."""
    refresh_token: str = Field(alias="refreshToken")


class LoginResponse(BaseModel):
    """Login response schema."""
    message: str
    uid: str
    email: str
    id_token: str = Field(alias="idToken")
    refresh_token: str = Field(alias="refreshToken")
    expires_in: str = Field(alias="expiresIn")


# Chat Schemas
class MessageInput(BaseModel):
    """Chat message input schema."""
    user_id: int | str
    message: str
    model_name: str
    session_id: str


class MessageResponse(BaseModel):
    """Chat message response schema."""
    reply: str


class SessionResponse(BaseModel):
    """Session response schema."""
    session_id: str
    user_id: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    message_count: int


class SessionsListResponse(BaseModel):
    """Sessions list response schema."""
    sessions: list[dict]
    count: int


class MessagesResponse(BaseModel):
    """Messages response schema."""
    session_id: str
    messages: list[dict]
    count: int


class DeleteResponse(BaseModel):
    """Delete response schema."""
    message: str
    document_id: Optional[str] = None
    session_id: Optional[str] = None
    messages_deleted: Optional[int] = None


# Document Chat Schemas
class QueryRequest(BaseModel):
    """Document query request schema."""
    question: str
    task_id: str


class QueryResponse(BaseModel):
    """Document query response schema."""
    question: str
    answer: str
    chunks_used: Optional[int] = 0
    source_documents: Optional[list[dict]] = Field(default_factory=list)


class UploadResponse(BaseModel):
    """Document upload response schema."""
    message: str
    task_id: str
    document_id: Optional[str] = None
    status: Optional[str] = None


class StatusResponse(BaseModel):
    """Processing status response schema."""
    processing: bool
    ready: bool
    status: Optional[str] = None
    filename: Optional[str] = None
    chunks_count: Optional[int] = None
    error: Optional[str] = None


class ChatRequest(BaseModel):
    """RAG chat request schema."""
    question: str
    task_id: str  # document_id (kept as task_id for backward compatibility)
    document_id: Optional[str] = Field(None, description="Optional document ID (alternative to task_id)")
    use_mmr: Optional[bool] = Field(True, description="Use Max Marginal Relevance retrieval")
    k: Optional[int] = Field(5, ge=1, le=20, description="Number of chunks to retrieve")


class ChatResponse(BaseModel):
    """RAG chat response schema."""
    question: str
    answer: str
    chunks_used: int
    source_documents: list[dict] = Field(default_factory=list)


# Resume Schemas
class ResumeAnalysisRequest(BaseModel):
    """Resume analysis request schema."""
    job_description: str


class GenerateResumeRequest(BaseModel):
    """Generate resume request schema."""
    resume_type: str
    resume_text: str
    job_description: str


class ResumeAnalysisResponse(BaseModel):
    """Resume analysis response schema."""
    analysis: str
    resume_text: str
    job_description: str


# RAG Schemas
class ChatRequest(BaseModel):
    """RAG chat request schema."""
    question: str
    document_id: Optional[str] = Field(None, description="Optional document ID to filter to specific document")
    use_mmr: Optional[bool] = Field(True, description="Use Max Marginal Relevance retrieval")
    use_multiquery: Optional[bool] = Field(False, description="Use MultiQuery retriever (requires OpenAI)")
    k: Optional[int] = Field(5, ge=1, le=20, description="Number of chunks to retrieve")


class ChatResponse(BaseModel):
    """RAG chat response schema."""
    question: str
    answer: str
    chunks_used: int
    source_documents: list[dict] = Field(default_factory=list)


class DocumentUploadResponse(BaseModel):
    """Document upload response schema."""
    document_id: str
    status: str
    message: str


class DocumentStatusResponse(BaseModel):
    """Document status response schema."""
    document_id: str
    status: str
    filename: Optional[str] = None
    chunks_count: Optional[int] = None
    created_at: Optional[str] = None
    error: Optional[str] = None

