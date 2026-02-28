# shared/jwt_utils.py
import os
from datetime import datetime, timedelta
from jose import jwt, JWTError, ExpiredSignatureError, JWSError
from dotenv import load_dotenv

load_dotenv()

SECRET_KEY = os.getenv("JWT_SECRET")
ALGORITHM = os.getenv("JWT_ALGORITHM")


def create_access_token(data: dict, expires_minutes: int = 60):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=expires_minutes)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("user_id")
        if not user_id:
            raise JWTError("Invalid token payload")
        return {"user_id": user_id, "email": payload.get("email")}
    except ExpiredSignatureError:
        raise JWTError("Token expired")
    except JWSError:
        raise JWTError("Signature verification failed")
    except JWTError as e:
        raise JWTError(f"Invalid token: {str(e)}")