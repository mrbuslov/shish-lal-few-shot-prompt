import shutil
from fastapi import APIRouter, Form, File, UploadFile, Depends, HTTPException, status
from fastapi.responses import JSONResponse
import asyncio
from typing import List, Optional
import base64
import os
import uuid
from datetime import datetime, timezone
from docx import Document
from pydantic import BaseModel
from src.fastapi_app.services import (
    process_single_text,
    transcribe_single_audio,
)
from src.fastapi_app.schemas import ProcessJsonRequest, UploadBase64Request
from src.fastapi_app.auth import get_current_user, get_current_admin_user
from src.utils.schemas import LlmStageOutput
from src.utils.local_docx_formatter import LocalDocxFormatter
from src.utils.consts import USER_REPORTS_FILES_DIR
from src.common.models import User, ReportData, TranscriptionProcessingResult, AllowedEmails
from src.common.db_facade import DatabaseFacade
from src.utils.utils import extract_text_from_docx

router = APIRouter(prefix="/api")


# Pydantic models for request/response
class ReportDataUpdate(BaseModel):
    few_shot_prompt: str = ""
    examples: str = ""
    important_notes: str = ""
    words_spelling: str = ""


@router.post("/process_text")
async def process_text(
    text: str = Form(...), current_user: User = Depends(get_current_user)
) -> JSONResponse:
    try:
        llm_result = await process_single_text(text, str(current_user.id))

        # Save result to TranscriptionProcessingResult
        transcription_facade = DatabaseFacade(TranscriptionProcessingResult)
        await transcription_facade.create(
            user_id=str(current_user.id),
            source_type="text",
            source_text=text,
            processing_result=llm_result.model_dump(),
        )

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
    request: UploadBase64Request, current_user: User = Depends(get_current_user)
) -> JSONResponse:
    try:
        # Prepare tasks for async processing
        tasks = {}

        for i, file in enumerate(request.files):
            if not file.filename.lower().endswith((".txt", ".docx", ".html")):
                continue

            # Decode base64 content
            try:
                file_bytes = base64.b64decode(file.content)
            except Exception as decode_error:
                print(f"Error decoding base64 for {file.filename}: {decode_error}")
                continue
            
            
            if file.filename.lower().endswith(".txt"):
                file_content = file_bytes.decode("utf-8")
            elif file.filename.lower().endswith(".docx"):
                file_content = extract_text_from_docx(file_bytes)
            else:
                raise ValueError(f"Unsupported file type: {file.filename}")

            # Add task for async processing
            task = process_single_text(
                file_content, str(current_user.id),
            )
            tasks[i] = {
                "task": task,
                "file_content": file_content,
                "filename": file.filename
            }

        if not tasks:
            return JSONResponse(
                content={"error": "No valid documents to process"}, status_code=400
            )

        task_results = await asyncio.gather(
            *[v['task'] for v in tasks.values()], 
            return_exceptions=True,
        )

        # Create results with file information and save to database
        json_results = []
        transcription_facade = DatabaseFacade(TranscriptionProcessingResult)

        for i, result in enumerate(task_results):
            if not isinstance(result, Exception):
                result_dict = result.model_dump()
                result_dict["source_type"] = "document"
                json_results.append(result_dict)

                # Save to database
                await transcription_facade.create(
                    user_id=str(current_user.id),
                    source_type="document",
                    source_text=tasks[i]['file_content'],
                    processing_result=result_dict,
                )

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
    processing_type: str = Form("transcription"),
    current_user: User = Depends(get_current_user)
) -> JSONResponse:
    try:
        # Prepare transcription tasks for async processing
        transcription_tasks = {}

        for i, file in enumerate(files):
            if not file.filename.lower().endswith((".mp3", ".m4a")):
                continue

            file_content = await file.read()
            # First gather: transcribe all audio files
            transcription_task = transcribe_single_audio(file_content, file.filename)
            transcription_tasks[i] = {
                "task": transcription_task,
                "filename": file.filename
            }

        if not transcription_tasks:
            return JSONResponse(
                content={"error": "No valid audio files to process"}, status_code=400
            )

        # First asyncio.gather: Transcribe all audio files in parallel
        transcription_results = await asyncio.gather(
            *[v['task'] for v in transcription_tasks.values()], 
            return_exceptions=True,
        )

        # Prepare processing tasks for transcribed texts
        processing_tasks = {}
        for i, transcription_result in enumerate(transcription_results):
            if not isinstance(transcription_result, Exception):
                # Determine additional prompt based on processing type
                additional_prompt = None
                if processing_type == "dictation":
                    additional_prompt = "You must keep everything that is dictated exactly as spoken in the letter content, preserving every word. However, when explicit field instructions are dictated (such as 'Plan: [content]', 'Diagnosis: [content]', etc.), extract that information to the appropriate field AND remove the explicit field instruction from the letter body. The letter should flow naturally without showing the dictated field labels."
                
                # Second gather: process all transcriptions as text
                processing_task = process_single_text(
                    transcription_result, str(current_user.id), additional_prompt=additional_prompt
                )
                processing_tasks[i] = {
                    "task": processing_task,
                    "transcribed_text": transcription_result,
                    "filename": transcription_tasks[i]['filename']
                }

        if not processing_tasks:
            return JSONResponse(
                content={"error": "No audio files could be transcribed successfully"},
                status_code=400,
            )

        # Second asyncio.gather: Process all transcriptions in parallel
        processing_results = await asyncio.gather(
            *[v['task'] for v in processing_tasks.values()], 
            return_exceptions=True,
        )

        # Create results with file information and save to database
        json_results = []
        transcription_facade = DatabaseFacade(TranscriptionProcessingResult)

        for i, result in enumerate(processing_results):
            if not isinstance(result, Exception):
                result_dict = result.model_dump()
                source_type = "audio_dictation" if processing_type == "dictation" else "audio"
                result_dict["source_type"] = source_type
                json_results.append(result_dict)

                # Save to database
                await transcription_facade.create(
                    user_id=str(current_user.id),
                    source_type=source_type,
                    source_text=processing_tasks[i]['transcribed_text'],
                    processing_result=result_dict,
                )

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
    request: dict, current_user: User = Depends(get_current_user)
) -> JSONResponse:
    try:
        # Extract data and patient_name from request
        data = LlmStageOutput(**request.get('data', {}))
        patient_name = request.get('patient_name')
        
        # Get user-specific template path or default
        from src.utils.utils import load_prompt_files, load_default_prompt_files_data

        try:
            user_prompts = await load_prompt_files(str(current_user.id))
            template_path = user_prompts.get(
                "report_file_url", "files/default_docx_report.docx"
            )

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
            base64_content = base64.b64encode(docx_content).decode("utf-8")

        # Clean up temp file
        os.remove(temp_path)

        # Extract patient name for filename
        final_patient_name = patient_name
        if not final_patient_name:
            # Fallback to extracting from recipients_info
            recipients_info = data_dict.get("recipients_info", "").strip()
            if recipients_info:
                # Convert HTML to text and take first line only
                import re
                # Remove HTML tags
                text_only = re.sub(r'<[^>]+>', '', recipients_info)
                # Take first line only
                first_line = text_only.split("\n")[0]
                final_patient_name = first_line.strip() if first_line else None
        
        if final_patient_name:
            # Remove "Patient Name:" prefix if present
            import re
            cleaned_name = re.sub(r'^Patient Name:\s*', '', final_patient_name, flags=re.IGNORECASE)
            
            # Clean patient name for safe filename - preserve hashtags, allow spaces
            # Remove only characters that are truly unsafe for filenames
            safe_name = re.sub(r'[<>:"/\\|?*]', '', cleaned_name)
            safe_name = safe_name.strip()
            
            # Only use the patient name if it's not empty after cleaning
            if safe_name:
                filename = safe_name + ".docx"
            else:
                filename = "medical_report.docx"
        else:
            filename = "medical_report.docx"

        return JSONResponse(
            content={"docx_base64": base64_content, "filename": filename}
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
                words_spelling=default_data.get("words_spelling", ""),
            )

        return JSONResponse(
            content={
                "few_shot_prompt": report_data.few_shot_prompt,
                "examples": report_data.examples,
                "important_notes": report_data.important_notes,
                "words_spelling": report_data.words_spelling,
                "report_file_url": report_data.report_file_url,
            }
        )
    except Exception as e:
        print(f"Error getting report data: {str(e)}")
        return JSONResponse(
            content={"error": "Failed to get report data"}, status_code=500
        )


@router.put("/report-data")
async def update_report_data(
    data: ReportDataUpdate, current_user: User = Depends(get_current_user)
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
                words_spelling=data.words_spelling,
            )
        else:
            # Update existing report data
            await report_facade.update_by_id(
                str(report_data.id),
                few_shot_prompt=data.few_shot_prompt,
                examples=data.examples,
                important_notes=data.important_notes,
                words_spelling=data.words_spelling,
                updated_at=datetime.now(timezone.utc),
            )

        return JSONResponse(content={"message": "Report data updated successfully"})
    except Exception as e:
        print(f"Error updating report data: {str(e)}")
        return JSONResponse(
            content={"error": "Failed to update report data"}, status_code=500
        )


@router.post("/upload-report-file")
async def upload_report_file(
    file: UploadFile = File(...), current_user: User = Depends(get_current_user)
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
            old_file_path = os.path.join(
                user_dir, report_data.report_file_url.split("/")[-1]
            )
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
                updated_at=datetime.now(timezone.utc),
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
                report_file_url=relative_path,
            )

        return JSONResponse(
            content={
                "message": "File uploaded successfully",
                "filename": unique_filename,
                "file_path": relative_path,
            }
        )
    except Exception as e:
        print(f"Error uploading file: {str(e)}")
        return JSONResponse(content={"error": "Failed to upload file"}, status_code=500)


@router.delete("/delete-report-file")
async def delete_report_file(current_user: User = Depends(get_current_user)):
    """Delete current user's report file"""
    try:
        report_facade = DatabaseFacade(ReportData)
        report_data = await report_facade.get_one(user_id=str(current_user.id))

        if not report_data or not report_data.report_file_url:
            return JSONResponse(content={"error": "No file to delete"}, status_code=404)

        # Delete the file from filesystem
        user_dir = os.path.join(USER_REPORTS_FILES_DIR, str(current_user.id))
        file_path = os.path.join(user_dir, report_data.report_file_url.split("/")[-1])
        if os.path.exists(file_path):
            os.remove(file_path)

        # Update report data to remove file reference
        await report_facade.update_by_id(
            str(report_data.id),
            report_file_url=None,
            updated_at=datetime.now(timezone.utc),
        )

        return JSONResponse(content={"message": "File deleted successfully"})
    except Exception as e:
        print(f"Error deleting file: {str(e)}")
        return JSONResponse(content={"error": "Failed to delete file"}, status_code=500)


@router.post("/admin/users")
async def get_users_list(email: str = Form(...), password: str = Form(...)):
    """Get all users list for admin"""
    try:
        # Verify admin credentials
        admin = await get_current_admin_user(email, password)
        if not admin:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid admin credentials",
            )

        # Fetch all users
        user_facade = DatabaseFacade(User)
        users = await user_facade.get_many()

        users_data = []
        for user in users:
            users_data.append(
                {
                    "id": str(user.id),
                    "email": user.email,
                    "full_name": user.full_name,
                    "is_active": user.is_active,
                    "is_superuser": user.is_superuser,
                    "created_at": (
                        user.created_at.isoformat() if user.created_at else None
                    ),
                    "updated_at": (
                        user.updated_at.isoformat() if user.updated_at else None
                    ),
                }
            )

        return JSONResponse(content={"users": users_data, "total": len(users_data)})
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error getting users list: {str(e)}")
        return JSONResponse(
            content={"error": "Failed to get users list"}, status_code=500
        )


@router.delete("/admin/users/{user_id}")
async def delete_user(user_id: str, email: str = Form(...), password: str = Form(...)):
    """Delete a user (admin only)"""
    try:
        # Verify admin credentials
        admin = await get_current_admin_user(email, password)
        if not admin:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid admin credentials",
            )

        # Check if user exists
        user_facade = DatabaseFacade(User)
        user = await user_facade.get_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
            )

        # Prevent self-deletion of admin
        if str(admin.id) == user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete your own admin account",
            )

        # Delete user's related data
        # Delete report data
        report_facade = DatabaseFacade(ReportData)
        await report_facade.delete_many(user_id=user_id)

        # Delete transcription results
        transcription_facade = DatabaseFacade(TranscriptionProcessingResult)
        await transcription_facade.delete_many(user_id=user_id)

        # Delete user files directory if exists
        user_dir = os.path.join(USER_REPORTS_FILES_DIR, user_id)
        if os.path.exists(user_dir):
            shutil.rmtree(user_dir)

        # Delete the user
        await user_facade.delete_by_id(user_id)

        return JSONResponse(
            content={"message": f"User {user.email} deleted successfully"}
        )

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error deleting user: {str(e)}")
        return JSONResponse(content={"error": "Failed to delete user"}, status_code=500)


@router.get("/history")
async def get_user_history(
    page: int = 1, per_page: int = 30, current_user: User = Depends(get_current_user)
):
    """Get user's transcription processing history with pagination"""
    try:
        transcription_facade = DatabaseFacade(TranscriptionProcessingResult)

        # Calculate skip
        skip = (page - 1) * per_page

        # Get total count
        total = await transcription_facade.count({"user_id": str(current_user.id)})

        # Get results with pagination, sorted by creation date (newest first)
        results = await transcription_facade.get_many(
            filters={"user_id": str(current_user.id)},
            skip=skip,
            limit=per_page,
            sort=[("created_at", -1)],
        )

        # Format results for frontend
        history_items = []
        for result in results:
            # Extract patient name and diagnosis from processing_result
            processing_data = result.processing_result
            patient_name = processing_data.get("recipients_info", "N/A")
            diagnosis = processing_data.get("diagnosis", "N/A")

            history_items.append(
                {
                    "id": str(result.id),
                    "patient_name": patient_name,
                    "diagnosis": diagnosis,
                    "source_type": result.source_type,
                    "created_at": result.created_at.isoformat(),
                    "processing_result": processing_data,
                }
            )

        # Calculate pagination info
        total_pages = (total + per_page - 1) // per_page
        has_next = page < total_pages
        has_prev = page > 1

        return JSONResponse(
            content={
                "items": history_items,
                "pagination": {
                    "page": page,
                    "per_page": per_page,
                    "total": total,
                    "total_pages": total_pages,
                    "has_next": has_next,
                    "has_prev": has_prev,
                },
            }
        )

    except Exception as e:
        print(f"Error getting user history: {str(e)}")
        return JSONResponse(
            content={"error": "Failed to get user history"}, status_code=500
        )


@router.get("/history/{result_id}")
async def get_history_item(
    result_id: str, current_user: User = Depends(get_current_user)
):
    """Get specific transcription processing result by ID"""
    try:
        transcription_facade = DatabaseFacade(TranscriptionProcessingResult)
        result = await transcription_facade.get_by_id(result_id)

        if not result or result.user_id != str(current_user.id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Result not found"
            )

        return JSONResponse(
            content={
                "id": str(result.id),
                "source_type": result.source_type,
                "processing_result": result.processing_result,
                "created_at": result.created_at.isoformat(),
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error getting history item: {str(e)}")
        return JSONResponse(
            content={"error": "Failed to get history item"}, status_code=500
        )


@router.post("/admin/allowed-emails/get")
async def get_allowed_emails(email: str = Form(...), password: str = Form(...)):
    """Get allowed emails list (admin only)"""
    try:
        # Verify admin credentials
        admin = await get_current_admin_user(email, password)
        if not admin:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid admin credentials",
            )

        allowed_emails_facade = DatabaseFacade(AllowedEmails)
        allowed_emails = await allowed_emails_facade.get_one()
        
        if not allowed_emails:
            # Create default empty allowed emails
            allowed_emails = await allowed_emails_facade.create(emails="")
        
        return JSONResponse(content={"emails": allowed_emails.emails})
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error getting allowed emails: {str(e)}")
        return JSONResponse(
            content={"error": "Failed to get allowed emails"}, status_code=500
        )


@router.post("/admin/allowed-emails")
async def update_allowed_emails(
    email: str = Form(...), password: str = Form(...), emails: str = Form(...)
):
    """Update allowed emails list (admin only)"""
    try:
        # Verify admin credentials
        admin = await get_current_admin_user(email, password)
        if not admin:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid admin credentials",
            )

        allowed_emails_facade = DatabaseFacade(AllowedEmails)
        existing = await allowed_emails_facade.get_one()
        
        if existing:
            await allowed_emails_facade.update_by_id(
                str(existing.id),
                emails=emails,
                updated_at=datetime.now(timezone.utc),
            )
        else:
            await allowed_emails_facade.create(emails=emails)
        
        return JSONResponse(content={"message": "Allowed emails updated successfully"})
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error updating allowed emails: {str(e)}")
        return JSONResponse(
            content={"error": "Failed to update allowed emails"}, status_code=500
        )
