from pydantic import BaseModel
from typing import Optional

class RawPage(BaseModel):
    book_id: str
    page: int
    text: str

class Chapter(BaseModel):
    book_id: str
    chapter_number: int
    chapter_name: str
    start_page: int
    end_page: int

class Topic(BaseModel):
    chapter_id: str
    topic_name: str
    explanation: Optional[str] = None
