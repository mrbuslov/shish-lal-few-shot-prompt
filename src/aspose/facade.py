import os
import zipfile
from http import HTTPMethod
from io import BytesIO
from random import randint

import html2text

from src.utils.schemas import FileData
from httpx_manager.httpx_manager import httpx_manager


class AsposeFacade:
    def __init__(self) -> None:
        self.base_url = "https://api.products.aspose.app/words/conversion/api/convert"
        self.url_docx_to_html = f"{self.base_url}?outputType=HTML"
        self.url_html_to_docx = f"{self.base_url}?outputType=DOCX"
        self.download_url_template = (
            "https://api.products.aspose.app/words/conversion/api/Download?id={file_id}"
        )
        self.headers = {
            "Origin": "https://products.aspose.app",
            "Referer": "https://products.aspose.app/",
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            "Accept": "*/*",
            "Accept-Encoding": "gzip, deflate, br, zstd",
            "Accept-Language": "en-US,en;q=0.9,ru;q=0.8",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
        }
        # self.headers = {
        #     "Accept": "*/*",
        #     "Accept-Encoding": "gzip, deflate, br, zstd",
        #     "Accept-Language": "en-US,en;q=0.9,ru;q=0.8",
        #     "Cache-Control": "no-cache",
        #     "Content-Type": "multipart/form-data; boundary=----WebKitFormBoundaryeZWtDXmwKPz4ogQu",
        #     "Origin": "https://products.aspose.app",
        #     "Pragma": "no-cache",
        #     "Referer": "https://products.aspose.app/",
        #     "Sec-CH-UA": '"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
        #     "Sec-CH-UA-Mobile": "?0",
        #     "Sec-CH-UA-Platform": '"Linux"',
        #     "Sec-Fetch-Dest": "empty",
        #     "Sec-Fetch-Mode": "cors",
        #     "Sec-Fetch-Site": "same-site",
        #     "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        # }

    async def docx_to_html(self, docx_file: bytes) -> list[FileData]:
        random_gen_num = randint(100, 999999999)
        files = {str(random_gen_num): docx_file}
        data = {
            "outputFileName": "dWFl",
            "ConversionOptions": '{"UseOcr":"false","Locale":"en","Password":null,"PageRange":null}',
        }

        response = await httpx_manager.async_request(
            url=self.url_docx_to_html,
            method=HTTPMethod.POST,
            headers=self.headers,
            files=files,
            data=data,
        )
        res_json = response.json()

        download_link = self.compile_download_link(res_json["id"])
        zip_archive_bytes = await self.download_file(download_link)
        return self.extract_zip_to_filedata(zip_archive_bytes)

    async def html_to_docx(self, html: str, file_name: str | None = None) -> FileData:
        random_gen_num = str(randint(100, 999999999))
        html_bytes = html.encode("utf-8")
        files = {
            # random_gen_num: ("file.html", html_bytes, "text/html"),
            random_gen_num: html_bytes,
            # "file": ("test.html", html.encode("utf-8"), "text/html"),
        }
        data = {
            "outputFileName": "dGVzdA==",
            "ConversionOptions": '{"UseOcr":"false","Locale":"en","Password":null,"PageRange":null}',
        }

        response = await httpx_manager.async_request(
            url=self.url_html_to_docx,
            method=HTTPMethod.POST,
            headers=self.headers,
            files=files,
            data=data,
        )

        res_json = response.json()
        file_id = res_json["id"]
        download_url = self.download_url_template.format(file_id=file_id)
        docx_bytes = await self.download_file(download_url)

        return FileData(
            path_name=file_name or file_id.split("/")[-1],
            extension="docx",
            file_bytes=docx_bytes,
            file_content=None,
        )

    @staticmethod
    async def download_file(download_url: str) -> bytes:
        """
        Download a file from URL to memory

        Args:
            download_url: URL to download the file from

        Returns:
            bytes: The downloaded file as bytes
        """
        response = await httpx_manager.async_request(
            url=download_url,
            method=HTTPMethod.GET,
        )
        if response.status_code == 200:
            return response.content
        else:
            raise Exception(
                f"Error downloading file: {response.status_code} {response.text}",
            )

    def compile_download_link(self, file_id: str) -> str:
        return self.download_url_template.format(file_id=file_id)

    @staticmethod
    def extract_zip_to_filedata(zip_bytes: bytes) -> list[FileData]:
        file_data_list = []

        with zipfile.ZipFile(BytesIO(zip_bytes)) as zip_file:
            for file_info in zip_file.infolist():
                if file_info.is_dir():
                    continue

                path_name = file_info.filename
                extension = os.path.splitext(path_name)[1][1:]  # remove the dot
                file_bytes = zip_file.read(path_name)

                try:
                    file_content = file_bytes.decode("utf-8")
                except UnicodeDecodeError:
                    file_content = None

                file_data_list.append(
                    FileData(
                        path_name=path_name,
                        extension=extension,
                        file_bytes=file_bytes,
                        file_content=file_content,
                    )
                )

        return file_data_list

    @staticmethod
    def html_to_txt(html_content: str) -> str:
        return html2text.html2text(html_content)


aspose_facade = AsposeFacade()
