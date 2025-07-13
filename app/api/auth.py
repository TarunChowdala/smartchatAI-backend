# main.py

from fastapi import APIRouter, HTTPException, Request, Header
from pydantic import BaseModel
from typing import Optional
import requests
from app.db.firestore_client import db
from firebase_admin import firestore, auth
from dotenv import load_dotenv
load_dotenv()
import os

router = APIRouter()

FIREBASE_API_KEY = os.getenv("FIREBASE_API_KEY")

def verify_token(request: Request):
    try:
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            raise HTTPException(status_code=401, detail="No valid authorization header")
            
        id_token = auth_header.split('Bearer ')[1]
        
        # Verify the token with Firebase Admin SDK
        decoded_token = auth.verify_id_token(id_token)
        return decoded_token
        
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Authentication failed: {str(e)}")

class LoginRequest(BaseModel):
    email: str
    password: str

class SignupRequest(BaseModel):
    email: str
    password: str
    name: str
    uid: str 
    idToken: str 
    about: Optional[str] = None

class googleSignUpRequest(BaseModel):
    email: str
    name : str
    uid : str
    idToken : str
    profileImage : str

class UpdateProfileRequest(BaseModel):
    email: str 
    name: str | None = None
    about: str | None = None

class UpdatePasswordRequest(BaseModel) :
    email: str
    current_password: str
    new_password: str

class RefreshTokenRequest(BaseModel):
    refreshToken: str

@router.post("/login")
def login_user(data: LoginRequest):
    # sign in with firebase api
    url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={FIREBASE_API_KEY}"
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

    # update the timestamp
    db.collection("users").document(user_id).update({
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

@router.post("/signup")
def signup_user(data: SignupRequest):
    user_id = data.uid 

    user_doc = db.collection("users").document(user_id)
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

@router.post("/google-signup")
def google_signup(data : googleSignUpRequest):
    user_id = data.uid

    user_doc = db.collection("users").document(user_id)
    user_doc.set({
        "uid": user_id,
        "email": data.email,
        "name": data.name,
        "profileImage": data.profileImage,
        "createdAt": firestore.SERVER_TIMESTAMP,
        "last_login": firestore.SERVER_TIMESTAMP,
        "role": "user"
    })

    return {
        "message": "User created successfully",
        "uid": user_id,
        "email": data.email
    }


@router.get("/me")
def get_logged_in_user(request: Request):
    try:
        user_data = verify_token(request)
        uid = user_data['uid']
        
        # Get user data from Firestore
        user_doc = db.collection("users").document(uid).get()
        if not user_doc.exists:
            raise HTTPException(status_code=404, detail="User not found in database")
        return user_doc.to_dict()
        
    except requests.Timeout:
        raise HTTPException(status_code=504, detail="Token verification timed out")
    except requests.RequestException as e:
        raise HTTPException(status_code=500, detail=f"Token verification failed: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Authentication failed: {str(e)}")


@router.post("/update-me")
def update_profile(request: Request, update_data: UpdateProfileRequest):
    try:
        # Verify token using existing function
        user_data = verify_token(request)
        uid = user_data['uid']
        
        # Find user by email in Firestore
        users_ref = db.collection("users")
        query = users_ref.where("email", "==", update_data.email).limit(1)
        results = query.get()
        
        if not results:
            raise HTTPException(status_code=404, detail="User not found")
            
        user_doc = results[0]
        
        # Prepare update data for Firestore
        update_dict = {}
        if update_data.name is not None:
            update_dict["name"] = update_data.name
        if update_data.about is not None:
            update_dict["about"] = update_data.about

        # Update the user document in Firestore
        if update_dict:
            user_doc.reference.update(update_dict)

        # Get updated user data
        updated_user = user_doc.reference.get()
        user_data = updated_user.to_dict()
        if 'password' in user_data:
            del user_data['password']
        return user_data

    except requests.Timeout:
        raise HTTPException(status_code=504, detail="Token verification timed out")
    except requests.RequestException as e:
        raise HTTPException(status_code=500, detail=f"Token verification failed: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Update failed: {str(e)}")



@router.post("/update-password")
def update_password(data: UpdatePasswordRequest):
    try:
        # First, sign in with current password to get a fresh token
        sign_in_url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={FIREBASE_API_KEY}"
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
        update_url = f"https://identitytoolkit.googleapis.com/v1/accounts:update?key={FIREBASE_API_KEY}"
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
        
    except requests.Timeout:
        raise HTTPException(status_code=504, detail="Request timed out")
    except requests.RequestException as e:
        raise HTTPException(status_code=500, detail=f"Request failed: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Update failed: {str(e)}")
    
