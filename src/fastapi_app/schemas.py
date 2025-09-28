from pydantic import BaseModel


class Base64File(BaseModel):
    filename: str
    content: str  # base64 encoded content
    content_type: str


class UploadBase64Request(BaseModel):
    files: list[Base64File]


class ProcessJsonRequest(BaseModel):
    documents: list[dict]
