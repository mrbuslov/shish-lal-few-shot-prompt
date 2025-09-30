from datetime import datetime
from typing import Optional
from beanie import Document, Indexed
from pydantic import Field
from pymongo import IndexModel


class User(Document):
    email: Indexed(str, unique=True)
    full_name: Optional[str] = None
    is_active: bool = Field(default=True)
    is_superuser: bool = Field(default=False)
    hashed_password: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "users"
        indexes = [
            IndexModel([("email", 1)], sparse=True),
        ]


class ReportData(Document):
    user_id: str = Field(..., description="Reference to User")
    few_shot_prompt: str = Field(default="")
    examples: str = Field(default="")
    important_notes: str = Field(default="")
    words_spelling: str = Field(default="")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "report_data"
        indexes = [
            IndexModel([("user_id", 1)]),
        ]
