import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")
DB_NAME = os.getenv("MONGO_DB")

client = AsyncIOMotorClient(MONGO_URI)

db = client[DB_NAME]

# example collection
users_collection = db["users"]
student_collection = db["students"] 