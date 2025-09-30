from fastapi import APIRouter, Form, File, UploadFile
from fastapi.responses import JSONResponse
import asyncio
from typing import List
import base64
import os
from docx import Document
from src.fastapi_app.services import (
    process_single_text,
    process_single_document,
    process_single_audio,
)
from src.utils.utils import load_prompt_files
from src.fastapi_app.schemas import ProcessJsonRequest, UploadBase64Request
from src.utils.schemas import LlmStageOutput
from src.utils.local_docx_formatter import LocalDocxFormatter

router = APIRouter(prefix="/api")


@router.post("/process_text")
async def process_text(text: str = Form(...)) -> JSONResponse:
    try:
        llm_result = await process_single_text(text)
        return JSONResponse(
            content={
                "json_data": llm_result.model_dump(),
            }
        )

    except Exception as e:
        print(f"Error processing text: {str(e)}")
        return JSONResponse(
            content={"error": "Failed to process text"}, status_code=500
        )


@router.post("/process_documents")
async def process_documents(request: UploadBase64Request) -> JSONResponse:
    try:
        # Prepare tasks for async processing
        tasks = []

        for file in request.files:
            if not file.filename.lower().endswith((".txt", ".docx", ".html")):
                continue

            # Decode base64 content
            try:
                file_bytes = base64.b64decode(file.content)
            except Exception as decode_error:
                print(f"Error decoding base64 for {file.filename}: {decode_error}")
                continue

            # Add task for async processing
            task = process_single_document(file_bytes, file.filename)
            tasks.append(task)

        if not tasks:
            return JSONResponse(
                content={"error": "No valid documents to process"}, status_code=400
            )

        processed_files = await asyncio.gather(*tasks, return_exceptions=True)
        valid_results = [f for f in processed_files if not isinstance(f, Exception)]
        if valid_results:
            return JSONResponse(
                content={
                    "json_results": [result.model_dump() for result in valid_results],
                    "count": len(valid_results),
                }
            )
        else:
            return JSONResponse(
                content={"error": "No documents could be processed successfully"},
                status_code=400,
            )

    except Exception as e:
        print(f"Error processing documents: {str(e)}")
        return JSONResponse(
            content={"error": "Failed to process documents"}, status_code=500
        )


@router.post("/process_audio")
async def process_audio(files: List[UploadFile] = File(...)) -> JSONResponse:
    try:
        # Prepare tasks for async processing
        tasks = []

        for file in files:
            if not file.filename.lower().endswith((".mp3", ".m4a")):
                continue

            file_content = await file.read()
            task = process_single_audio(file_content, file.filename)
            tasks.append(task)
        if not tasks:
            return JSONResponse(
                content={"error": "No valid audio files to process"}, status_code=400
            )

        processed_files = await asyncio.gather(*tasks, return_exceptions=True)
        valid_results = [f for f in processed_files if not isinstance(f, Exception)]
        if valid_results:
            return JSONResponse(
                content={
                    "json_results": [result.model_dump() for result in valid_results],
                    "count": len(valid_results),
                }
            )
        else:
            return JSONResponse(
                content={"error": "No audio files could be processed successfully"},
                status_code=400,
            )

    except Exception as e:
        print(f"Error processing audio files: {str(e)}")
        return JSONResponse(
            content={"error": "Failed to process audio files"}, status_code=500
        )


@router.post("/process_json")
async def process_json(request: ProcessJsonRequest) -> JSONResponse:
    try:
        if not request.document:
            return JSONResponse(
                content={"error": "No documents provided"}, status_code=400
            )

        # Load the template HTML
        prompts_data = load_prompt_files()
        template_html = prompts_data.get("output_example", "")

        if not template_html:
            return JSONResponse(
                content={"error": "Template not found"}, status_code=500
            )

        formatted_data = dict(request.document)
        final_html = template_html
        for key, value in formatted_data.items():
            final_html = final_html.replace("{{" + key + "}}", str(value))

        return JSONResponse(
            content={
                "json_results": [formatted_data],
                "count": 1,
            }
        )

    except Exception as e:
        print(f"Error in process_json endpoint: {str(e)}")
        return JSONResponse(
            content={"error": "Failed to process JSON data"}, status_code=500
        )


@router.post("/download_docx")
async def download_docx(data: LlmStageOutput) -> JSONResponse:
    try:
        # Load the default DOCX template
        template_path = "files/default_docx_report.docx"
        if not os.path.exists(template_path):
            return JSONResponse(
                content={"error": "DOCX template not found"}, status_code=500
            )
        
        # Load template document
        doc = Document(template_path)
        
        # Initialize formatter
        formatter = LocalDocxFormatter()
        
        # Replace placeholders with values from LlmStageOutput
        data_dict = data.model_dump()
        for key, value in data_dict.items():
            if value is not None:
                placeholder = "{" + key + "}"
                # Convert value to string, handle None values
                str_value = str(value) if value is not None else ""
                formatter.replace_all(doc, placeholder, str_value, html=True)
        
        # Save to temporary file and encode to base64
        temp_path = "/tmp/filled_report.docx"
        doc.save(temp_path)
        
        with open(temp_path, "rb") as file:
            docx_content = file.read()
            base64_content = base64.b64encode(docx_content).decode('utf-8')
        
        # Clean up temp file
        os.remove(temp_path)
        
        return JSONResponse(
            content={
                "docx_base64": base64_content,
                "filename": "medical_report.docx"
            }
        )
        
    except Exception as e:
        print(f"Error in download_docx endpoint: {str(e)}")
        return JSONResponse(
            content={"error": "Failed to generate DOCX document"}, status_code=500
        )
