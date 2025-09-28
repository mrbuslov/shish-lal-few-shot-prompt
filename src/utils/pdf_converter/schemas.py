"""
Data schemas for local conversion
"""

from dataclasses import dataclass


@dataclass
class FileData:
    """File data structure compatible with existing system"""

    file_bytes: bytes
    path_name: str
    content_type: str = "application/pdf"

    @classmethod
    def from_conversion_result(cls, result):
        """Create FileData from ConversionResult"""
        return cls(
            file_bytes=result.pdf_bytes,
            path_name=result.filename,
            content_type=result.content_type,
        )
