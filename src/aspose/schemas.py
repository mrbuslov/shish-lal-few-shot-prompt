from typing import Optional

from pydantic import BaseModel


class FileData(BaseModel):
    path_name: str
    extension: str
    file_bytes: bytes
    file_content: Optional[str] = None
