from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import settings

client = AsyncIOMotorClient(settings.MONGO_URI)
db = client[settings.DATABASE_NAME]

quizzes_collection = db["quizzes"]
evaluations_collection = db["evaluations"]
students_collection = db["students"]