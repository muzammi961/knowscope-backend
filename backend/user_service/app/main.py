from dotenv import load_dotenv
load_dotenv()
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.routes.auth import auth_router
from app.routes.students import student_router




app = FastAPI(title="Knowscope User Service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# app.include_router(router)
app.include_router(auth_router)
app.include_router(student_router)


app.mount("/uploads", StaticFiles(directory="app/uploads"), name="uploads")

@app.get("/")
async def root():
    return {"status": "user service running"}