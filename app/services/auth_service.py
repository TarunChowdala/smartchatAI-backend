"""Authentication service for user management."""
import requests
from fastapi import HTTPException
from firebase_admin import firestore
from app.config import settings
from app.db.firestore_client import get_firestore_db
from app.models.schemas import (
    LoginRequest,
    SignupRequest,
    GoogleSignupRequest,
    UpdateProfileRequest,
    UpdatePasswordRequest,
)


class AuthService:
    """Service for authentication operations."""
    
    def __init__(self):
        self.db = get_firestore_db()
        self.firebase_api_key = settings.firebase_api_key
    
    def login(self, data: LoginRequest) -> dict:
        """
        Authenticate user with email and password.
        
        Args:
            data: Login request data
            
        Returns:
            Login response with tokens and user info
            
        Raises:
            HTTPException: If credentials are invalid
        """
        url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={self.firebase_api_key}"
        payload = {
            "email": data.email,
            "password": data.password,
            "returnSecureToken": True
        }
        
        response = requests.post(url, json=payload)
        
        if response.status_code != 200:
            raise HTTPException(status_code=401, detail="Invalid credentials")
        
        res_data = response.json()
        user_id = res_data["localId"]
        
        # Update last login timestamp
        self.db.collection("users").document(user_id).update({
            "last_login": firestore.SERVER_TIMESTAMP
        })
        
        return {
            "message": "User logged in successfully",
            "uid": user_id,
            "email": res_data["email"],
            "idToken": res_data["idToken"],
            "refreshToken": res_data["refreshToken"],
            "expiresIn": res_data["expiresIn"]
        }
    
    def signup(self, data: SignupRequest) -> dict:
        """
        Create new user account.
        
        Args:
            data: Signup request data
            
        Returns:
            Signup response with user info
        """
        user_id = data.uid
        
        user_doc = self.db.collection("users").document(user_id)
        user_doc.set({
            "name": data.name,
            "uid": user_id,
            "email": data.email,
            "about": data.about if data.about else "",
            "createdAt": firestore.SERVER_TIMESTAMP,
            "last_login": firestore.SERVER_TIMESTAMP,
            "role": "user"
        })
        
        return {
            "message": "User created successfully",
            "uid": user_id,
            "email": data.email
        }
    
    def google_signup(self, data: GoogleSignupRequest) -> dict:
        """
        Create new user account via Google OAuth.
        
        Args:
            data: Google signup request data
            
        Returns:
            Signup response with user info
        """
        user_id = data.uid
        
        user_doc = self.db.collection("users").document(user_id)
        user_doc.set({
            "uid": user_id,
            "email": data.email,
            "name": data.name,
            "profileImage": data.profile_image,
            "createdAt": firestore.SERVER_TIMESTAMP,
            "last_login": firestore.SERVER_TIMESTAMP,
            "role": "user"
        })
        
        return {
            "message": "User created successfully",
            "uid": user_id,
            "email": data.email
        }
    
    def get_user(self, uid: str) -> dict:
        """
        Get user data by UID.
        
        Args:
            uid: User ID
            
        Returns:
            User data dictionary
            
        Raises:
            HTTPException: If user not found
        """
        user_doc = self.db.collection("users").document(uid).get()
        if not user_doc.exists:
            raise HTTPException(status_code=404, detail="User not found in database")
        return user_doc.to_dict()
    
    def update_profile(self, email: str, update_data: UpdateProfileRequest, uid: str) -> dict:
        """
        Update user profile.
        
        Args:
            email: User email
            update_data: Update profile request data
            uid: User ID from token
            
        Returns:
            Updated user data
            
        Raises:
            HTTPException: If user not found or update fails
        """
        users_ref = self.db.collection("users")
        query = users_ref.where("email", "==", email).limit(1)
        results = query.get()
        
        if not results:
            raise HTTPException(status_code=404, detail="User not found")
        
        user_doc = results[0]
        
        # Verify the user owns this profile
        if user_doc.id != uid:
            raise HTTPException(status_code=403, detail="Not authorized to update this profile")
        
        # Prepare update data
        update_dict = {}
        if update_data.name is not None:
            update_dict["name"] = update_data.name
        if update_data.about is not None:
            update_dict["about"] = update_data.about
        
        # Update the user document
        if update_dict:
            user_doc.reference.update(update_dict)
        
        # Get updated user data
        updated_user = user_doc.reference.get()
        user_data = updated_user.to_dict()
        if 'password' in user_data:
            del user_data['password']
        return user_data
    
    def update_password(self, data: UpdatePasswordRequest) -> dict:
        """
        Update user password.
        
        Args:
            data: Update password request data
            
        Returns:
            New tokens after password update
            
        Raises:
            HTTPException: If current password is incorrect or update fails
        """
        # First, sign in with current password to get a fresh token
        sign_in_url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={self.firebase_api_key}"
        sign_in_response = requests.post(sign_in_url, json={
            "email": data.email,
            "password": data.current_password,
            "returnSecureToken": True
        })
        
        if sign_in_response.status_code != 200:
            raise HTTPException(status_code=401, detail="Current password is incorrect")
        
        # Get the fresh token
        fresh_token = sign_in_response.json()["idToken"]
        
        # Update the password
        update_url = f"https://identitytoolkit.googleapis.com/v1/accounts:update?key={self.firebase_api_key}"
        update_response = requests.post(update_url, json={
            "idToken": fresh_token,
            "password": data.new_password,
            "returnSecureToken": True
        })
        
        if update_response.status_code != 200:
            raise HTTPException(status_code=400, detail="Failed to update password")
        
        # Return the new tokens
        new_tokens = update_response.json()
        return {
            "message": "Password updated successfully",
            "idToken": new_tokens.get("idToken"),
            "refreshToken": new_tokens.get("refreshToken"),
            "expiresIn": new_tokens.get("expiresIn")
        }


# Singleton instance
auth_service = AuthService()

