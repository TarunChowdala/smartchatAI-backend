"""Service for enforcing usage limits on free tier."""
from typing import Optional
from fastapi import HTTPException
from firebase_admin import firestore
from app.db.firestore_client import get_firestore_db


class UsageLimitService:
    """Service to manage and enforce user quotas."""
    
    # Limits
    MAX_SESSIONS = 2
    MAX_MESSAGES_PER_SESSION = 30
    MAX_DOCUMENTS = 2
    MAX_RESUME_GENERATIONS = 2

    def __init__(self):
        self.db = get_firestore_db()

    def is_admin(self, user_id: str) -> bool:
        """Check if user has admin role."""
        try:
            if not user_id:
                return False
            user_doc = self.db.collection("users").document(user_id).get()
            if user_doc.exists:
                data = user_doc.to_dict()
                return data.get("role") == "admin"
        except Exception:
            return False
        return False

    def check_session_limit(self, user_id: str):
        """Check if user has reached max sessions (2)."""
        if self.is_admin(user_id):
            return

        sessions_ref = self.db.collection("sessions")
        # Query sessions belonging to user
        query = sessions_ref.where("user_id", "==", user_id).stream()
        count = sum(1 for _ in query)
        
        if count >= self.MAX_SESSIONS:
            raise HTTPException(
                status_code=403,
                detail=f"Usage limit reached: You can only create up to {self.MAX_SESSIONS} chat sessions on the free tier."
            )

    def check_message_limit(self, session_id: str, user_id: str = None):
        """Check if session has reached max messages (20)."""
        if user_id and self.is_admin(user_id):
            return

        messages_ref = self.db.collection("sessions").document(session_id).collection("messages")
        # Efficiently count messages
        count = len(list(messages_ref.stream()))
        
        if count >= self.MAX_MESSAGES_PER_SESSION:
            raise HTTPException(
                status_code=403,
                detail=f"Session limit reached: You can only send up to {self.MAX_MESSAGES_PER_SESSION} messages per session."
            )

    def check_document_limit(self, user_id: str):
        """Check if user has reached max documents (2)."""
        if self.is_admin(user_id):
            return

        docs_ref = self.db.collection("documents")
        query = docs_ref.where("user_id", "==", user_id).stream()
        count = sum(1 for _ in query)
        
        if count >= self.MAX_DOCUMENTS:
            raise HTTPException(
                status_code=403,
                detail=f"Document limit reached: You can only upload up to {self.MAX_DOCUMENTS} documents on the free tier."
            )

    def check_resume_limit(self, user_id: str):
        """Check if user has reached max resume generations (2)."""
        if self.is_admin(user_id):
            return

        user_ref = self.db.collection("users").document(user_id)
        user_doc = user_ref.get()
        
        if user_doc.exists:
            data = user_doc.to_dict()
            count = data.get("resume_generation_count", 0)
            if count >= self.MAX_RESUME_GENERATIONS:
                raise HTTPException(
                    status_code=403,
                    detail=f"Resume limit reached: You can only generate/analyze up to {self.MAX_RESUME_GENERATIONS} resumes on the free tier."
                )
        return user_ref

    def get_user_usage(self, user_id: str) -> dict:
        """Get usage statistics for a user."""
        # Sessions count
        sessions_query = self.db.collection("sessions").where("user_id", "==", user_id).stream()
        sessions_count = sum(1 for _ in sessions_query)
        
        # Documents count
        docs_query = self.db.collection("documents").where("user_id", "==", user_id).stream()
        docs_count = sum(1 for _ in docs_query)
        
        # Resume count
        user_doc = self.db.collection("users").document(user_id).get()
        resume_count = 0
        role = "user"
        if user_doc.exists:
            user_data = user_doc.to_dict()
            resume_count = user_data.get("resume_generation_count", 0)
            role = user_data.get("role", "user")

        return {
            "user_id": user_id,
            "role": role,
            "usage": {
                "sessions": {
                    "current": sessions_count,
                    "limit": self.MAX_SESSIONS if role != "admin" else "unlimited"
                },
                "documents": {
                    "current": docs_count,
                    "limit": self.MAX_DOCUMENTS if role != "admin" else "unlimited"
                },
                "resumes": {
                    "current": resume_count,
                    "limit": self.MAX_RESUME_GENERATIONS if role != "admin" else "unlimited"
                },
                "messages_per_session_limit": self.MAX_MESSAGES_PER_SESSION if role != "admin" else "unlimited"
            }
        }

    def reset_usage(self, target_user_id: str, admin_user_id: str):
        """Reset usage limits for a specific user (Admin only)."""
        if not self.is_admin(admin_user_id):
            raise HTTPException(status_code=403, detail="Only admins can reset usage limits")
        
        # Reset resume count in user document
        user_ref = self.db.collection("users").document(target_user_id)
        if user_ref.get().exists:
            user_ref.update({
                "resume_generation_count": 0,
                "updated_at": firestore.SERVER_TIMESTAMP
            })
        
        return {"message": f"Usage limits reset for user {target_user_id}"}

    def list_all_users_usage(self, admin_user_id: str, limit: int = 100) -> list:
        """List all users and their usage (Admin only)."""
        if not self.is_admin(admin_user_id):
            raise HTTPException(status_code=403, detail="Only admins can view all users usage")
            
        users_ref = self.db.collection("users").limit(limit).stream()
        users_usage = []
        
        for user_doc in users_ref:
            user_id = user_doc.id
            usage = self.get_user_usage(user_id)
            user_data = user_doc.to_dict()
            usage["email"] = user_data.get("email", "N/A")
            usage["name"] = user_data.get("name", "N/A")
            users_usage.append(usage)
            
        return users_usage

    def increment_resume_count(self, user_id: str):
        """Increment the resume generation counter for a user."""
        user_ref = self.db.collection("users").document(user_id)
        user_ref.update({
            "resume_generation_count": firestore.Increment(1),
            "updated_at": firestore.SERVER_TIMESTAMP
        })


# Singleton instance
usage_limit_service = UsageLimitService()

