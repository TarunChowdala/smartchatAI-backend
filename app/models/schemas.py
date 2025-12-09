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


# Document Chat Schemas
class QueryRequest(BaseModel):
    """Document query request schema."""
    question: str
    task_id: str


class QueryResponse(BaseModel):
    """Document query response schema."""
    question: str
    answer: str


class UploadResponse(BaseModel):
    """Document upload response schema."""
    message: str
    task_id: str


class StatusResponse(BaseModel):
    """Processing status response schema."""
    processing: bool
    ready: bool


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

