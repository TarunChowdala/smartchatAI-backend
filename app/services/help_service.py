"""Service for managing help queries and support tickets."""
import uuid
from typing import List, Optional
from firebase_admin import firestore
from fastapi import HTTPException
from app.db.firestore_client import get_firestore_db
from app.services.usage_limit_service import usage_limit_service


class HelpService:
    """Service for chat operations."""
    
    def __init__(self):
        self.db = get_firestore_db()
        self.collection_name = "help_queries"

    def submit_query(self, user_id: str, subject: str, message: str) -> dict:
        """Submit a new help query."""
        query_id = str(uuid.uuid4())
        db_data = {
            "id": query_id,
            "user_id": user_id,
            "subject": subject,
            "message": message,
            "status": "open",
            "reply": None,
            "created_at": firestore.SERVER_TIMESTAMP,
            "updated_at": firestore.SERVER_TIMESTAMP
        }
        
        self.db.collection(self.collection_name).document(query_id).set(db_data)
        
        # Return serializable data (SERVER_TIMESTAMP is not JSON serializable)
        import datetime
        response_data = db_data.copy()
        now_iso = datetime.datetime.now().isoformat()
        response_data["created_at"] = now_iso
        response_data["updated_at"] = now_iso
        
        return response_data

    def get_user_queries(self, user_id: str) -> List[dict]:
        """Get all queries for a specific user."""
        # Remove order_by from Firestore to avoid composite index requirement
        docs = self.db.collection(self.collection_name).where("user_id", "==", user_id).stream()
        
        queries = []
        for doc in docs:
            queries.append(doc.to_dict())
            
        # Sort in Python instead
        queries.sort(key=lambda x: str(x.get('created_at') or ''), reverse=True)
        return queries

    def get_all_queries(self, admin_user_id: str, status: Optional[str] = None) -> List[dict]:
        """Get all queries (Admin only)."""
        if not usage_limit_service.is_admin(admin_user_id):
            raise HTTPException(status_code=403, detail="Admin access required")
            
        query_ref = self.db.collection(self.collection_name)
        
        if status:
            docs = query_ref.where("status", "==", status).stream()
        else:
            docs = query_ref.stream()
            
        queries = []
        for doc in docs:
            queries.append(doc.to_dict())
            
        # Sort in Python instead
        queries.sort(key=lambda x: str(x.get('created_at') or ''), reverse=True)
        return queries

    def reply_to_query(self, admin_user_id: str, query_id: str, reply: str) -> dict:
        """Reply to a query (Admin only)."""
        if not usage_limit_service.is_admin(admin_user_id):
            raise HTTPException(status_code=403, detail="Admin access required")
            
        doc_ref = self.db.collection(self.collection_name).document(query_id)
        doc = doc_ref.get()
        
        if not doc.exists:
            raise HTTPException(status_code=404, detail="Query not found")
            
        doc_ref.update({
            "reply": reply,
            "status": "in_progress",
            "updated_at": firestore.SERVER_TIMESTAMP
        })
        
        return {"message": "Reply submitted successfully", "query_id": query_id}

    def update_status(self, admin_user_id: str, query_id: str, status: str) -> dict:
        """Update status of a query (Admin only)."""
        if not usage_limit_service.is_admin(admin_user_id):
            raise HTTPException(status_code=403, detail="Admin access required")
            
        valid_statuses = ["open", "in_progress", "resolved", "closed"]
        if status not in valid_statuses:
            raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of: {valid_statuses}")
            
        doc_ref = self.db.collection(self.collection_name).document(query_id)
        if not doc_ref.get().exists:
            raise HTTPException(status_code=404, detail="Query not found")
            
        doc_ref.update({
            "status": status,
            "updated_at": firestore.SERVER_TIMESTAMP
        })
        
        return {"message": f"Status updated to {status}", "query_id": query_id}


# Singleton instance
help_service = HelpService()

