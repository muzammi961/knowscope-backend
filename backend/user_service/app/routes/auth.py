# from fastapi import APIRouter
# from app.auth.google import verify_google_token
# from app.crud import get_user_by_google_id, create_user, serialize_user
# from app.schemas import GoogleAuthRequest, UserResponse, AuthResponse
# from app.auth.jwt import create_access_token

# auth_router = APIRouter()
# auth_router = APIRouter(prefix="/auth", tags=["auth"])


# @auth_router.post("/google/auth", response_model=AuthResponse)
# async def google_auth(payload: GoogleAuthRequest):
#     user_data = verify_google_token(payload.token)

#     user = await get_user_by_google_id(user_data["google_id"])
#     if not user:
#         user = await create_user(user_data)

#     serialized_user = serialize_user(user)

#     token = create_access_token({
#         "user_id": serialized_user["id"],
#         "email": serialized_user["email"]
#     })

#     return {
#         "access_token": token,
#         "user": serialized_user
#     }
    
    
    
    
    
import os
from datetime import datetime, timedelta
from jose import jwt
from dotenv import load_dotenv
from fastapi import APIRouter, HTTPException

from app.auth.google import verify_google_token
from app.crud import get_user_by_google_id, create_user, serialize_user
from app.schemas import GoogleAuthRequest, AuthResponse
from .jwt_handler import create_access_token

# Load .env
load_dotenv()

SECRET_KEY = os.getenv("JWT_SECRET")
ALGORITHM = os.getenv("JWT_ALGORITHM")

auth_router = APIRouter(prefix="/auth", tags=["auth"])

@auth_router.post("/google/auth", response_model=AuthResponse)
async def google_auth(payload: GoogleAuthRequest):
    try:
        user_data = verify_google_token(payload.token)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid Google token")

    user = await get_user_by_google_id(user_data["google_id"])
    if not user:
        user = await create_user(user_data)

    serialized_user = serialize_user(user)
    
    token = create_access_token({
        "user_id": serialized_user["id"],
        "email": serialized_user["email"]
    })
    
    return {"access_token": token, "user": serialized_user}    