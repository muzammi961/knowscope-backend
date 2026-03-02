import os
from datetime import datetime, timedelta
from jose import jwt
from dotenv import load_dotenv
from jose import JWTError, ExpiredSignatureError, JWSError
from fastapi import HTTPException

load_dotenv()

SECRET_KEY = os.getenv("JWT_SECRET")
ALGORITHM = os.getenv("JWT_ALGORITHM")

<<<<<<< HEAD
def create_access_token(data: dict, expires_minutes: int = 60):
=======
def create_access_token(data: dict, expires_minutes: int = 10080):
>>>>>>> upstream/developer
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=expires_minutes)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

<<<<<<< HEAD
=======
# def create_refresh_token(data: dict, expires_days: int = 14):
#     to_encode = data.copy()
#     expire = datetime.utcnow() + timedelta(days=expires_days)
#     to_encode.update({"exp": expire,"type": "refresh"})
#     return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
>>>>>>> upstream/developer



def get_current_user(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("user_id")
<<<<<<< HEAD
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token payload")
        return {"user_id": user_id}
    except ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
=======
        role = payload.get("role")
        if not user_id or not role:
            raise HTTPException(status_code=401, detail="Invalid token payload")
        return {"user_id": user_id, "role": role,"email": payload.get("email")}
    except ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    
    
    
>>>>>>> upstream/developer
