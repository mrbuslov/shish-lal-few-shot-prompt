from datetime import datetime, timezone
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
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

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
    report_file_url: Optional[str] = Field(default=None)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Settings:
        name = "report_data"
        indexes = [
            IndexModel([("user_id", 1)]),
        ]


class TranscriptionProcessingResult(Document):
    user_id: str = Field(..., description="Reference to User")
    source_type: str = Field(..., description="Type of source: text, document, audio")
    source_text: str = Field(
        ..., description="Input text or transcription that was processed"
    )
    processing_result: dict = Field(..., description="JSON result from LLM processing")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Settings:
        name = "transcription_processing_results"
        indexes = [
            IndexModel([("user_id", 1)]),
            IndexModel([("created_at", -1)]),
            IndexModel([("user_id", 1), ("created_at", -1)]),
        ]


class AllowedEmails(Document):
    emails: str = Field(..., description="Comma-separated list of allowed email addresses")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Settings:
        name = "allowed_emails"
