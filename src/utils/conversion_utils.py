import zipfile
from io import BytesIO
from typing import List, Optional

import html2text


class FileData:
    def __init__(
        self,
        path_name: str,
        extension: str,
        file_bytes: bytes,
        file_content: Optional[str] = None,
    ):
        self.path_name = path_name
        self.extension = extension
        self.file_bytes = file_bytes
        self.file_content = file_content


class ConversionUtils:
    @staticmethod
    def html_to_simple_docx(html_content: str, filename: str = "output") -> FileData:
        """
        Creates a simple DOCX-like file from HTML content.
        For this implementation, we'll create a basic RTF file which can be opened by Word.
        """
        # Convert HTML to RTF (Rich Text Format) which is compatible with Word
        rtf_content = ConversionUtils._html_to_rtf(html_content)
        rtf_bytes = rtf_content.encode("utf-8")

        return FileData(
            path_name=f"{filename}.rtf",
            extension="rtf",
            file_bytes=rtf_bytes,
            file_content=rtf_content,
        )

    @staticmethod
    def html_to_txt(html_content: str) -> str:
        return html2text.html2text(html_content)

    @staticmethod
    def _html_to_rtf(html_content: str) -> str:
        """
        Convert HTML to RTF format (basic conversion)
        """
        # RTF header
        rtf_content = r"{\rtf1\ansi\deff0 {\fonttbl {\f0 Times New Roman;}}}"

        # Basic HTML to RTF conversion
        content = html_content

        # Remove HTML tags and convert basic formatting
        import re

        # Convert paragraphs
        content = re.sub(r"<p[^>]*>", r"\\par ", content)
        content = re.sub(r"</p>", r"\\par\\par ", content)

        # Convert headers
        content = re.sub(r"<h[1-6][^>]*>", r"\\b\\fs24 ", content)
        content = re.sub(r"</h[1-6]>", r"\\b0\\fs20\\par ", content)

        # Convert bold
        content = re.sub(r"<b[^>]*>", r"\\b ", content)
        content = re.sub(r"</b>", r"\\b0 ", content)
        content = re.sub(r"<strong[^>]*>", r"\\b ", content)
        content = re.sub(r"</strong>", r"\\b0 ", content)

        # Convert italic
        content = re.sub(r"<i[^>]*>", r"\\i ", content)
        content = re.sub(r"</i>", r"\\i0 ", content)
        content = re.sub(r"<em[^>]*>", r"\\i ", content)
        content = re.sub(r"</em>", r"\\i0 ", content)

        # Convert line breaks
        content = re.sub(r"<br[^>]*>", r"\\par ", content)

        # Remove remaining HTML tags
        content = re.sub(r"<[^>]+>", "", content)

        # Escape RTF special characters
        content = content.replace("\\", "\\\\")
        content = content.replace("{", "\\{")
        content = content.replace("}", "\\}")

        rtf_content += content + "}"

        return rtf_content

    @staticmethod
    def create_zip_archive(files: List[FileData]) -> bytes:
        """
        Create a ZIP archive containing multiple files
        """
        zip_buffer = BytesIO()

        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
            for file_data in files:
                zip_file.writestr(file_data.path_name, file_data.file_bytes)

        zip_buffer.seek(0)
        return zip_buffer.getvalue()


# Create instance for easy import
conversion_utils = ConversionUtils()
