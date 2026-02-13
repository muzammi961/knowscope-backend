from pydantic import BaseModel, EmailStr
from typing import Optional

class GoogleAuthRequest(BaseModel):
    token: str

class UserResponse(BaseModel):
    id: str
    email: EmailStr
    name: str | None = None
    picture: str | None = None

class AuthResponse(BaseModel):
    access_token: str
    user: UserResponse
    
    
    
    
    # Student Schemas
class StudentCreate(BaseModel):
    name: str
    class_number: int
    medium: str

class StudentResponse(BaseModel):
    id: str
    name: str
    class_number: int
    medium: str
    image: Optional[str]
    created_by: Optional[str] 
    learningstyle:str