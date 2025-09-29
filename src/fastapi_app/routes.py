from fastapi import APIRouter, Form, File, UploadFile
from fastapi.responses import JSONResponse
import asyncio
from typing import List
from src.fastapi_app.services import (
    process_single_text,
    process_single_document,
    process_single_audio,
)
from src.utils.utils import load_prompt_files
import base64
from src.fastapi_app.schemas import ProcessJsonRequest, UploadBase64Request

router = APIRouter(prefix="/api")


@router.post("/process_text")
async def process_text(text: str = Form(...)) -> JSONResponse:
    try:
        dict_res, html_result = await process_single_text(text)
        return JSONResponse(
            content={
                "json_data": dict_res.model_dump(),
                "html_result": html_result,
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
                    "html_results": valid_results,
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
                    "html_results": valid_results,
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
                "html_results": [final_html],
                "count": 1,
            }
        )

    except Exception as e:
        print(f"Error in process_json endpoint: {str(e)}")
        return JSONResponse(
            content={"error": "Failed to process JSON data"}, status_code=500
        )
