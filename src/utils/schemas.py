from typing import Optional
from pydantic import BaseModel, Field


class FileData(BaseModel):
    path_name: str
    extension: str
    file_bytes: bytes
    file_content: Optional[str] = None

    class Config:
        arbitrary_types_allowed = True


class LlmStageOutput(BaseModel):
    reasoning: str | None = Field(None, description="Very short thoughts what fields you're going to fill in with what values - abstract")
    recipients_info: str | None = Field(None, description="Recipients info")
    diagnosis: str | None = Field(None, description="Diagnosis")
    corrected_visual_acuity_right: str | None = Field(
        None, description="Corrected visual acuity right. Format: 6/6"
    )
    corrected_visual_acuity_left: str | None = Field(
        None, description="Corrected visual acuity left. Format: 6/12"
    )
    next_review: str | None = Field(None, description="str format")
    letter_to_patient: str | None = Field(None, description="Letter to patient. ONLY in plain text format")
