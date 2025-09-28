from fastapi import APIRouter, Form, File, UploadFile
from fastapi.responses import StreamingResponse, JSONResponse
import asyncio
from typing import List
from io import BytesIO
from src.utils.consts import OUTPUT_REPORT_CONTENT_PARAGRAPH_BLOCK
from src.utils.conversion_utils import ConversionUtils
from src.fastapi_app.services import (
    create_zip_archive,
    process_single_text,
    process_single_document,
    process_single_audio,
    OUTPUT_FORMAT,
    load_prompt_files,
)
from src.utils.pdf_converter import html_to_pdf
from src.utils.pdf_converter.schemas import FileData as LocalFileData
import base64
from src.fastapi_app.services import process_stage_one, process_stage_two, OUTPUT_FORMAT
import json
import base64
from src.fastapi_app.schemas import ProcessJsonRequest, UploadBase64Request

router = APIRouter(prefix="/api")


@router.post("/process_text")
async def process_text(text: str = Form(...)):
    """Process text input and return JSON data with original file"""
    try:
        # Process the text using the main service
        file_data, json_res = await process_single_text(text, "processed_document.pdf")

        # Return base64 response with JSON data
        file_base64 = base64.b64encode(file_data.file_bytes).decode("utf-8")

        # Handle letter_to_patient format conversion for the form
        if isinstance(json_res.get("letter_to_patient"), list):
            json_res["letter_to_patient_text"] = "\n\n".join(
                json_res["letter_to_patient"]
            )
        else:
            json_res["letter_to_patient_text"] = str(
                json_res.get("letter_to_patient", "")
            )
        json_res["letter_to_patient_text"] = ConversionUtils.html_to_txt(
            json_res["letter_to_patient_text"]
        )

        return JSONResponse(
            content={
                "json_data": json_res,
                "file_data": file_base64,
                "filename": file_data.path_name,
                "content_type": "application/pdf",
            }
        )

    except Exception as e:
        print(f"Error processing text: {str(e)}")
        return JSONResponse(
            content={"error": "Failed to process text"}, status_code=500
        )


@router.post("/process_documents")
async def process_documents(request: UploadBase64Request):
    """Process uploaded document files and return ZIP with processed documents"""
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

        # Process all files concurrently
        processed_files = await asyncio.gather(*tasks, return_exceptions=True)

        # Filter out exceptions
        valid_files = [f for f in processed_files if not isinstance(f, Exception)]
        print(f"valid_files length: {len(valid_files)}")

        if valid_files:
            # Return base64 response for both single and multiple files
            if len(valid_files) == 1:
                file_data = valid_files[0]
                # Ensure filename has .pdf extension
                filename = file_data.path_name
                if not filename.lower().endswith(".pdf"):
                    filename = filename.rsplit(".", 1)[0] + ".pdf"

                file_base64 = base64.b64encode(file_data.file_bytes).decode("utf-8")

                return JSONResponse(
                    content={
                        "file_data": file_base64,
                        "filename": filename,
                        "content_type": "application/pdf",
                        "is_zip": False,
                    }
                )
            else:
                # Create ZIP archive for multiple documents
                zip_bytes = create_zip_archive(valid_files)
                zip_base64 = base64.b64encode(zip_bytes).decode("utf-8")

                return JSONResponse(
                    content={
                        "file_data": zip_base64,
                        "filename": "processed_documents.zip",
                        "content_type": "application/zip",
                        "is_zip": True,
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
async def process_audio(files: List[UploadFile] = File(...)):
    """Process uploaded audio files and return ZIP with processed documents"""
    try:
        # Prepare tasks for async processing
        tasks = []

        for file in files:
            if not file.filename.lower().endswith((".mp3", ".m4a")):
                continue

            # Read file content
            file_content = await file.read()

            # Add task for async processing
            task = process_single_audio(file_content, file.filename)
            tasks.append(task)

        if not tasks:
            return JSONResponse(
                content={"error": "No valid audio files to process"}, status_code=400
            )

        # Process all files concurrently
        processed_files = await asyncio.gather(*tasks, return_exceptions=True)

        # Filter out exceptions
        valid_files = [f for f in processed_files if not isinstance(f, Exception)]

        if valid_files:
            # Return base64 response for both single and multiple files
            if len(valid_files) == 1:
                file_data = valid_files[0]
                # Ensure filename has .pdf extension
                filename = file_data.path_name
                if not filename.lower().endswith(".pdf"):
                    filename = filename.rsplit(".", 1)[0] + ".pdf"

                file_base64 = base64.b64encode(file_data.file_bytes).decode("utf-8")

                return JSONResponse(
                    content={
                        "file_data": file_base64,
                        "filename": filename,
                        "content_type": "application/pdf",
                        "is_zip": False,
                    }
                )
            else:
                # Create ZIP archive for multiple audio files
                zip_bytes = create_zip_archive(valid_files)
                zip_base64 = base64.b64encode(zip_bytes).decode("utf-8")

                return JSONResponse(
                    content={
                        "file_data": zip_base64,
                        "filename": "processed_audio.zip",
                        "content_type": "application/zip",
                        "is_zip": True,
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
async def process_json(request: ProcessJsonRequest):
    """Process JSON data with OUTPUT_FORMAT fields and generate DOCX documents directly (no LLM)"""
    try:
        if not request.documents:
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

        processed_files = []

        for idx, doc_data in enumerate(request.documents):
            try:
                # Validate that document contains expected OUTPUT_FORMAT fields
                for field in OUTPUT_FORMAT.keys():
                    if field not in doc_data:
                        return JSONResponse(
                            content={
                                "error": f"Missing required field: {field} in document {idx + 1}"
                            },
                            status_code=400,
                        )

                # Format letter_to_patient if it's a list
                formatted_data = dict(doc_data)
                if isinstance(formatted_data.get("letter_to_patient"), list):
                    formatted_data["letter_to_patient"] = "\n".join(
                        [
                            f'<p style="text-align:justify; font-size:10pt"><span style="font-family:Arial">{paragraph}</span></p>'
                            for paragraph in formatted_data["letter_to_patient"]
                        ]
                    )

                # Generate HTML from template directly (no LLM processing)
                final_html = template_html
                for key, value in formatted_data.items():
                    final_html = final_html.replace("{{" + key + "}}", str(value))

                # Convert to DOCX
                filename = f"processed_document_{idx + 1}.pdf"
                conversion_result = html_to_pdf(final_html, filename)
                file_data = LocalFileData.from_conversion_result(conversion_result)
                processed_files.append(file_data)

            except Exception as e:
                print(f"Error processing document {idx + 1}: {str(e)}")
                continue

        if not processed_files:
            return JSONResponse(
                content={"error": "No documents could be processed"}, status_code=400
            )

        # Return single DOCX if only one document, otherwise ZIP
        if len(processed_files) == 1:
            file_data = processed_files[0]
            # Ensure filename has .pdf extension
            filename = file_data.path_name
            if not filename.lower().endswith(".pdf"):
                filename = filename.rsplit(".", 1)[0] + ".pdf"

            return StreamingResponse(
                BytesIO(file_data.file_bytes),
                media_type="application/pdf",
                headers={"Content-Disposition": f"attachment; filename={filename}"},
            )
        else:
            # Create ZIP for multiple documents
            zip_bytes = create_zip_archive(processed_files)
            return StreamingResponse(
                BytesIO(zip_bytes),
                media_type="application/zip",
                headers={
                    "Content-Disposition": "attachment; filename=processed_documents.zip"
                },
            )

    except Exception as e:
        print(f"Error in process_json endpoint: {str(e)}")
        return JSONResponse(
            content={"error": "Failed to process JSON data"}, status_code=500
        )


@router.post("/process_text_complete")
async def process_text_complete(text: str = Form(...)):
    """Process text input and return both JSON data and ZIP file URL"""
    try:

        # Process through both stages
        stage_one_result = await process_stage_one(text)
        stage_two_result = await process_stage_two(stage_one_result)

        # Extract JSON data from stage 1 processing
        try:
            print(f"Stage 1 result for JSON parsing: {stage_one_result[:500]}...")
            # Stage 1 already returns clean JSON (without markdown markers)
            json_data = json.loads(stage_two_result.strip())

            # Handle letter_to_patient format conversion for the form
            if isinstance(json_data.get("letter_to_patient"), list):
                json_data["letter_to_patient_text"] = "\n\n".join(
                    json_data["letter_to_patient"]
                )
            else:
                json_data["letter_to_patient_text"] = str(
                    json_data.get("letter_to_patient", "")
                )

        except Exception as parse_error:
            print(f"JSON parsing error: {parse_error}")
            print(f"Stage 1 result that failed to parse: {stage_one_result}")
            # Fallback: create basic structure
            json_data = {key: "" for key in OUTPUT_FORMAT.keys()}
            json_data["letter_to_patient"] = ["Generated content not available"]
            json_data["letter_to_patient_text"] = "Generated content not available"

        json_data["letter_to_patient_text"] = "\n".join(
            [
                OUTPUT_REPORT_CONTENT_PARAGRAPH_BLOCK.format(paragraph=p)
                for p in json_data["letter_to_patient_text"]
            ]
        )

        # Generate the original file (single DOCX, not ZIP for one document)
        conversion_result = html_to_pdf(stage_two_result, "processed_document.pdf")
        file_data = LocalFileData.from_conversion_result(conversion_result)

        # For single document, return DOCX directly
        file_base64 = base64.b64encode(file_data.file_bytes).decode("utf-8")

        return JSONResponse(
            content={
                "json_data": json_data,
                "file_data": file_base64,
                "filename": file_data.path_name,
                "content_type": "application/pdf",
            }
        )

    except Exception as e:
        print(f"Error processing text complete: {str(e)}")
        return JSONResponse(
            content={"error": "Failed to process text"}, status_code=500
        )


@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}
