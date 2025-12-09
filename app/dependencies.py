"""Dependency injection for FastAPI routes."""
from fastapi import Depends, Request
from app.core.security import verify_firebase_token, get_current_user_uid
from app.db.firestore_client import get_firestore_db


def get_current_user(request: Request) -> dict:
    """
    Dependency to get current authenticated user from token.
    
    Usage:
        @router.get("/protected")
        def protected_route(user: dict = Depends(get_current_user)):
            return {"uid": user["uid"]}
    """
    return verify_firebase_token(request)


def get_current_user_id(request: Request) -> str:
    """
    Dependency to get current user UID.
    
    Usage:
        @router.get("/protected")
        def protected_route(uid: str = Depends(get_current_user_id)):
            return {"uid": uid}
    """
    return get_current_user_uid(request)


def get_db():
    """
    Dependency to get Firestore database instance.
    
    Usage:
        @router.get("/data")
        def get_data(db = Depends(get_db)):
            return db.collection("users").get()
    """
    return get_firestore_db()

