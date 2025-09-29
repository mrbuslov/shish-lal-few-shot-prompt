import zipfile
from io import BytesIO
from typing import List

import html2text


from src.utils.schemas import FileData


class ConversionUtils:

    @staticmethod
    def create_zip_archive(files: List[FileData]) -> bytes:
        """Create a ZIP archive containing multiple files"""
        zip_buffer = BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
            for file_data in files:
                zip_file.writestr(file_data.path_name, file_data.file_bytes)
        zip_buffer.seek(0)
        return zip_buffer.getvalue()

    @staticmethod
    def html_to_txt(html_content: str) -> str:
        return html2text.html2text(html_content)


# Create instance for easy import
conversion_utils = ConversionUtils()
