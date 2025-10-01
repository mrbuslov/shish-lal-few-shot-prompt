from fastapi import APIRouter, Form, File, UploadFile, Depends, HTTPException, status
from fastapi.responses import JSONResponse
import asyncio
from typing import List, Optional
import base64
import os
import uuid
from datetime import datetime
from docx import Document
from pydantic import BaseModel
from src.fastapi_app.services import (
    process_single_text,
    process_single_document,
    process_single_audio,
)
from src.fastapi_app.schemas import ProcessJsonRequest, UploadBase64Request
from src.fastapi_app.auth import get_current_user, get_current_admin_user
from src.utils.schemas import LlmStageOutput
from src.utils.local_docx_formatter import LocalDocxFormatter
from src.utils.consts import USER_REPORTS_FILES_DIR
from src.common.models import User, ReportData
from src.common.db_facade import DatabaseFacade

router = APIRouter(prefix="/api")

# Pydantic models for request/response
class ReportDataUpdate(BaseModel):
    few_shot_prompt: str = ""
    examples: str = ""
    important_notes: str = ""
    words_spelling: str = ""


@router.post("/process_text")
async def process_text(
    text: str = Form(...),
    current_user: User = Depends(get_current_user)
) -> JSONResponse:
    try:
        llm_result = await process_single_text(text, str(current_user.id))
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
async def process_documents(
    request: UploadBase64Request,
    current_user: User = Depends(get_current_user)
) -> JSONResponse:
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
            task = process_single_document(file_bytes, file.filename, str(current_user.id))
            tasks.append((task, file.filename))

        if not tasks:
            return JSONResponse(
                content={"error": "No valid documents to process"}, status_code=400
            )

        task_results = await asyncio.gather(*[task for task, filename in tasks], return_exceptions=True)
        
        # Create results with file information
        json_results = []
        for i, result in enumerate(task_results):
            if not isinstance(result, Exception):
                result_dict = result.model_dump()
                result_dict["source_filename"] = tasks[i][1]
                result_dict["source_type"] = "document"
                json_results.append(result_dict)
        
        if json_results:
            return JSONResponse(
                content={
                    "json_results": json_results,
                    "count": len(json_results),
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
async def process_audio(
    files: List[UploadFile] = File(...),
    current_user: User = Depends(get_current_user)
) -> JSONResponse:
    try:
        # Prepare tasks for async processing
        tasks = []

        for file in files:
            if not file.filename.lower().endswith((".mp3", ".m4a")):
                continue

            file_content = await file.read()
            task = process_single_audio(file_content, file.filename, str(current_user.id))
            tasks.append((task, file.filename))
        if not tasks:
            return JSONResponse(
                content={"error": "No valid audio files to process"}, status_code=400
            )

        task_results = await asyncio.gather(*[task for task, filename in tasks], return_exceptions=True)
        
        # Create results with file information
        json_results = []
        for i, result in enumerate(task_results):
            if not isinstance(result, Exception):
                result_dict = result.model_dump()
                result_dict["source_filename"] = tasks[i][1]
                result_dict["source_type"] = "audio"
                json_results.append(result_dict)
        
        if json_results:
            return JSONResponse(
                content={
                    "json_results": json_results,
                    "count": len(json_results),
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


@router.post("/download_docx")
async def download_docx(
    data: LlmStageOutput, 
    current_user: User = Depends(get_current_user)
) -> JSONResponse:
    try:
        # Get user-specific template path or default
        from src.utils.utils import load_prompt_files, load_default_prompt_files_data
        try:
            user_prompts = await load_prompt_files(str(current_user.id))
            template_path = user_prompts.get("report_file_url", "files/default_docx_report.docx")
            
            # Handle user-specific files path
            if template_path and not template_path.startswith("files/"):
                template_path = os.path.join("files/user_reports", template_path)
        except Exception:
            # Fallback to default
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


@router.get("/report-data")
async def get_report_data(current_user: User = Depends(get_current_user)):
    """Get current user's report data"""
    try:
        report_facade = DatabaseFacade(ReportData)
        report_data = await report_facade.get_one(user_id=str(current_user.id))
        
        if not report_data:
            # Create default report data if none exists
            from src.utils.utils import load_default_prompt_files_data
            default_data = load_default_prompt_files_data()
            report_data = await report_facade.create(
                user_id=str(current_user.id),
                few_shot_prompt=default_data.get("few_shot_prompt", ""),
                examples=default_data.get("examples", ""),
                important_notes=default_data.get("important_notes", ""),
                words_spelling=default_data.get("words_spelling", "")
            )
        
        return JSONResponse(
            content={
                "few_shot_prompt": report_data.few_shot_prompt,
                "examples": report_data.examples,
                "important_notes": report_data.important_notes,
                "words_spelling": report_data.words_spelling,
                "report_file_url": report_data.report_file_url
            }
        )
    except Exception as e:
        print(f"Error getting report data: {str(e)}")
        return JSONResponse(
            content={"error": "Failed to get report data"}, status_code=500
        )


@router.put("/report-data")
async def update_report_data(
    data: ReportDataUpdate,
    current_user: User = Depends(get_current_user)
):
    """Update current user's report data"""
    try:
        report_facade = DatabaseFacade(ReportData)
        report_data = await report_facade.get_one(user_id=str(current_user.id))
        
        if not report_data:
            # Create new report data
            report_data = await report_facade.create(
                user_id=str(current_user.id),
                few_shot_prompt=data.few_shot_prompt,
                examples=data.examples,
                important_notes=data.important_notes,
                words_spelling=data.words_spelling
            )
        else:
            # Update existing report data
            await report_facade.update_by_id(
                str(report_data.id),
                few_shot_prompt=data.few_shot_prompt,
                examples=data.examples,
                important_notes=data.important_notes,
                words_spelling=data.words_spelling,
                updated_at=datetime.utcnow()
            )
        
        return JSONResponse(
            content={"message": "Report data updated successfully"}
        )
    except Exception as e:
        print(f"Error updating report data: {str(e)}")
        return JSONResponse(
            content={"error": "Failed to update report data"}, status_code=500
        )


@router.post("/upload-report-file")
async def upload_report_file(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user)
):
    """Upload report file for current user"""
    try:
        # Create user-specific directory
        user_dir = os.path.join(USER_REPORTS_FILES_DIR, str(current_user.id))
        os.makedirs(user_dir, exist_ok=True)
        
        # Get current report data to check for existing file
        report_facade = DatabaseFacade(ReportData)
        report_data = await report_facade.get_one(user_id=str(current_user.id))
        
        # Delete previous file if exists
        if report_data and report_data.report_file_url:
            old_file_path = os.path.join(user_dir, report_data.report_file_url.split('/')[-1])
            if os.path.exists(old_file_path):
                os.remove(old_file_path)
        
        # Generate unique filename
        file_extension = os.path.splitext(file.filename)[1]
        unique_filename = f"{uuid.uuid4()}{file_extension}"
        file_path = os.path.join(user_dir, unique_filename)
        
        # Save the file
        content = await file.read()
        with open(file_path, "wb") as f:
            f.write(content)
        
        # Update report data with new file path
        relative_path = f"{current_user.id}/{unique_filename}"
        if report_data:
            await report_facade.update_by_id(
                str(report_data.id),
                report_file_url=relative_path,
                updated_at=datetime.utcnow()
            )
        else:
            # Create new report data with file
            from src.utils.utils import load_default_prompt_files_data
            default_data = load_default_prompt_files_data()
            await report_facade.create(
                user_id=str(current_user.id),
                few_shot_prompt=default_data.get("few_shot_prompt", ""),
                examples=default_data.get("examples", ""),
                important_notes=default_data.get("important_notes", ""),
                words_spelling=default_data.get("words_spelling", ""),
                report_file_url=relative_path
            )
        
        return JSONResponse(
            content={
                "message": "File uploaded successfully",
                "filename": unique_filename,
                "file_path": relative_path
            }
        )
    except Exception as e:
        print(f"Error uploading file: {str(e)}")
        return JSONResponse(
            content={"error": "Failed to upload file"}, status_code=500
        )


@router.delete("/delete-report-file")
async def delete_report_file(current_user: User = Depends(get_current_user)):
    """Delete current user's report file"""
    try:
        report_facade = DatabaseFacade(ReportData)
        report_data = await report_facade.get_one(user_id=str(current_user.id))
        
        if not report_data or not report_data.report_file_url:
            return JSONResponse(
                content={"error": "No file to delete"}, status_code=404
            )
        
        # Delete the file from filesystem
        user_dir = os.path.join(USER_REPORTS_FILES_DIR, str(current_user.id))
        file_path = os.path.join(user_dir, report_data.report_file_url.split('/')[-1])
        if os.path.exists(file_path):
            os.remove(file_path)
        
        # Update report data to remove file reference
        await report_facade.update_by_id(
            str(report_data.id),
            report_file_url=None,
            updated_at=datetime.utcnow()
        )
        
        return JSONResponse(
            content={"message": "File deleted successfully"}
        )
    except Exception as e:
        print(f"Error deleting file: {str(e)}")
        return JSONResponse(
            content={"error": "Failed to delete file"}, status_code=500
        )


@router.post("/admin/users")
async def get_users_list(email: str = Form(...), password: str = Form(...)):
    """Get all users list for admin"""
    try:
        # Verify admin credentials
        if not await get_current_admin_user(email, password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid admin credentials"
            )
        
        # Fetch all users
        user_facade = DatabaseFacade(User)
        users = await user_facade.get_many()
        
        users_data = []
        for user in users:
            users_data.append({
                "id": str(user.id),
                "email": user.email,
                "full_name": user.full_name,
                "is_active": user.is_active,
                "is_superuser": user.is_superuser,
                "created_at": user.created_at.isoformat() if user.created_at else None,
                "updated_at": user.updated_at.isoformat() if user.updated_at else None
            })
        
        return JSONResponse(
            content={
                "users": users_data,
                "total": len(users_data)
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error getting users list: {str(e)}")
        return JSONResponse(
            content={"error": "Failed to get users list"}, status_code=500
        )
