import os
from uuid import uuid4
from fastapi import UploadFile

UPLOAD_DIR = "app/uploads"

async def save_image(image: UploadFile) -> str:
    if not os.path.exists(UPLOAD_DIR):
        os.makedirs(UPLOAD_DIR)

    ext = image.filename.split(".")[-1]
    filename = f"{uuid4()}.{ext}"
    filepath = os.path.join(UPLOAD_DIR, filename)

    content = await image.read()  # async read
    with open(filepath, "wb") as f:
        f.write(content)

    return filename
