from fastapi import APIRouter
from app.auth.google import verify_google_token
from app.crud import get_user_by_google_id, create_user, serialize_user
from app.schemas import GoogleAuthRequest, UserResponse, AuthResponse
from app.auth.jwt import create_access_token

auth_router = APIRouter()
auth_router = APIRouter(prefix="/auth", tags=["auth"])


@auth_router.post("/google/auth", response_model=AuthResponse)
async def google_auth(payload: GoogleAuthRequest):
    user_data = verify_google_token(payload.token)

    user = await get_user_by_google_id(user_data["google_id"])
    if not user:
        user = await create_user(user_data)

    serialized_user = serialize_user(user)

    token = create_access_token({
        "user_id": serialized_user["id"],
        "email": serialized_user["email"]
    })

    return {
        "access_token": token,
        "user": serialized_user
    }
    
    
    
    