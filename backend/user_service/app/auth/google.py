import os
from google.oauth2 import id_token
from google.auth.transport import requests
from fastapi import HTTPException, status

def verify_google_token(token: str) -> dict:
    GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")

    if not GOOGLE_CLIENT_ID:
        raise RuntimeError("GOOGLE_CLIENT_ID is not set")

    try:
        idinfo = id_token.verify_oauth2_token(
            token,
            requests.Request(),
            GOOGLE_CLIENT_ID
        )

        if idinfo["iss"] not in (
            "accounts.google.com",
            "https://accounts.google.com",
        ):
            raise ValueError("Wrong issuer")

        return {
            "google_id": idinfo["sub"],
            "email": idinfo["email"],
            "name": idinfo.get("name"),
            "picture": idinfo.get("picture"),
        }

    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Google token",
        )
