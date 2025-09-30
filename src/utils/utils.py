import os
import tempfile
import time
from io import BytesIO

from docx import Document
from openai import AsyncOpenAI
from dotenv import load_dotenv

from src.common.settings import settings
from src.common.models import ReportData
from src.common.db_facade import DatabaseFacade

load_dotenv()

openai_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)


def extract_text_from_docx(docx_bytes: bytes) -> str:
    """Extract text from DOCX file using python-docx"""
    try:
        doc = Document(BytesIO(docx_bytes))
        text_content = []

        for paragraph in doc.paragraphs:
            if paragraph.text.strip():
                text_content.append(paragraph.text)

        return "\n".join(text_content)
    except Exception as e:
        print(f"Error extracting text from DOCX: {str(e)}")
        raise


async def load_prompt_files(user_id: str) -> dict:
    """Load prompt files data for a specific user from MongoDB"""
    
    report_facade = DatabaseFacade(ReportData)
    report_data = await report_facade.get_one(user_id=user_id)
    
    if not report_data:
        # If no user-specific data found, return default data
        return load_default_prompt_files_data()
    
    # Check if report_file_url is None, load from local file
    if report_data.report_file_url is None:
        report_file_url = "files/default_docx_report.docx"
    else:
        report_file_url = report_data.report_file_url
    
    return {
        "few_shot_prompt": report_data.few_shot_prompt,
        "examples": report_data.examples,
        "important_notes": report_data.important_notes,
        "words_spelling": report_data.words_spelling,
        "report_file_url": report_file_url,
    }
    
    
def load_default_prompt_files_data() -> dict:
    """Load all required prompt files"""
    base_path = "files/prompts_default"
    files = {
        "few_shot_prompt": f"{base_path}/few-shot-prompt.md",
        "examples": f"{base_path}/examples.json",
        "important_notes": f"{base_path}/important_notes.md",
        "words_spelling": f"{base_path}/words_spelling.json",
    }

    data = {}
    for key, file_path in files.items():
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                if file_path.endswith(".json"):
                    data[key] = f.read()  # Keep as string for now
                else:
                    data[key] = f.read()
        except FileNotFoundError:
            print(f"Warning: {file_path} not found")
            data[key] = ""

    return data


def clean_json_from_response(response: str) -> str:
    """Clean JSON from AI response by removing markdown and extra text"""
    return response.replace("```json", "").replace("```", "").strip()


async def transcribe_audio_with_openai(audio_bytes: bytes, filename: str) -> str:
    """Transcribe audio using OpenAI's Whisper API"""
    try:
        # Create temporary file
        file_ext = os.path.splitext(filename)[1] if filename else ".mp3"
        temp_file_path = create_temp_audio_file(audio_bytes, file_ext)

        try:
            # Transcribe using OpenAI API
            transcription = await transcribe_with_file(temp_file_path)
            return transcription
        finally:
            # Clean up temporary file
            cleanup_temp_file(temp_file_path)

    except Exception as e:
        print(f"Error in audio transcription: {str(e)}")
        raise


def create_temp_audio_file(audio_bytes: bytes, file_ext: str) -> str:
    """Create a temporary audio file and return its path"""
    try:
        # Create temp file with proper extension
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as temp_file:
            temp_file.write(audio_bytes)
            return temp_file.name
    except Exception as e:
        print(f"Error creating temp file: {str(e)}")
        raise


async def transcribe_with_file(file_path: str) -> str:
    """Transcribe audio file using OpenAI API"""
    try:
        print(f"Transcribing audio file: {file_path}")

        with open(file_path, "rb") as audio_file:
            transcript = await openai_client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                response_format="text",
            )

        print("Audio transcription completed successfully")
        return transcript

    except Exception as e:
        print(f"Error in OpenAI transcription: {str(e)}")
        raise


def cleanup_temp_file(file_path: str, max_attempts: int = 5):
    """Clean up temporary file with retry logic"""
    for attempt in range(max_attempts):
        try:
            os.unlink(file_path)
            print(f"Successfully cleaned up temp file: {file_path}")
            return
        except Exception as e:
            if attempt < max_attempts - 1:
                # Wait before retry, increasing delay each time
                time.sleep(0.1 * (2**attempt))
            else:
                print(f"Warning: Could not delete temp file {file_path}: {str(e)}")
