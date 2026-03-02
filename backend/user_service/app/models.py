from datetime import datetime

def user_document(data: dict) -> dict:
    return {
        "google_id": data["google_id"],
        "email": data["email"],
        "name": data.get("name"),
        "picture": data.get("picture"),
        "created_at": datetime.utcnow()
    }
