from typing import Optional
from fastapi import APIRouter, UploadFile, Form, Depends
from app.database import student_collection
from app.utils import save_image
from app.Jwt_utils.auth import get_current_user
from bson import ObjectId

student_router = APIRouter(prefix="/students", tags=["Students"])

def objectid_to_str(obj):
    if isinstance(obj, ObjectId):
        return str(obj)
    return obj
@student_router.post("/create")
async def create_student(
    name: str = Form(...),
    class_number: int = Form(...),
    medium: str = Form(...),
    image: Optional[UploadFile] = None,
    current_user: dict = Depends(get_current_user),
    learningstyle:str=Form(...)
):
    image_name = await save_image(image) if image else None
    created_by = objectid_to_str(current_user["user_id"])
    student = {
        "name": name,
        "class_number": class_number,
        "medium": medium,
        "image": image_name,
        "created_by": created_by,
        "learningstyle":learningstyle
    }
    result = await student_collection.insert_one(student)
    response_data = {"id": str(result.inserted_id),**student}
    response_data = {k: objectid_to_str(v) for k, v in response_data.items()}
    return response_data


@student_router.get("/authenticateduser")
async def get_my_profile(current_user: dict = Depends(get_current_user)):
    student = await student_collection.find_one({"created_by": str(current_user["user_id"])})
    if not student:
        return {"error": "Student profile not found for this user"}
    return {
        "id": str(student["_id"]),
        "name": student.get("name"),
        "class_number": student.get("class_number"),
        "medium": student.get("medium"),
        "image": student.get("image"),
        "created_by": student.get("created_by"),
        "learningstyle": student.get("learningstyle", None)
    }




@student_router.get("/get")
async def get_students():
    students = []
    async for s in student_collection.find():
        students.append({
            "id": str(s["_id"]),
            "name": s["name"],
            "class_number": s["class_number"],
            "medium": s["medium"],
            "image": s.get("image"),
            "created_by":s['created_by'],
            "learningstyle": s.get("learningstyle", None) 
        })
    return students


@student_router.get("/getonespecific/{student_id}")
async def get_student(student_id: str):
    student = await student_collection.find_one({"_id": ObjectId(student_id)})
    if not student:
        return {"error": "Student not found"}
    return {
        "id": str(student["_id"]),
        "name": student["name"],
        "class_number": student["class_number"],
        "medium": student["medium"],
        "image": student.get("image"),
        "created_by":student.get('created_by'),
        "learningstyle":student.get("learningstyle",None)
    }
