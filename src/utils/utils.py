import os
import tempfile
import time
import asyncio
from io import BytesIO

from docx import Document
from openai import AsyncOpenAI
from dotenv import load_dotenv
from pydub import AudioSegment

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
    """Load all required prompt files with fallback defaults"""
    # Default fallback data in case files can't be loaded
    default_data = {
        "few_shot_prompt": "Default few shot prompt",
        "examples": "[]",
        "important_notes": "Default important notes",
        "words_spelling": "{}",
        "report_file_url": "files/default_docx_report.docx",
    }

    # Try to load from files
    base_path = "files/prompts_default"
    files = {
        "few_shot_prompt": f"{base_path}/few-shot-prompt.md",
        "examples": f"{base_path}/examples.json",
        "important_notes": f"{base_path}/important_notes.md",
        "words_spelling": f"{base_path}/words_spelling.json",
    }

    data = default_data.copy()  # Start with defaults

    for key, file_path in files.items():
        try:
            # Check if file exists first
            if not os.path.exists(file_path):
                print(f"Warning: {file_path} not found, using default")
                continue

            # Try different encodings
            content = ""
            for encoding in ["utf-8", "utf-8-sig", "latin1", "cp1252"]:
                try:
                    with open(file_path, "r", encoding=encoding) as f:
                        content = f.read()
                    data[key] = content  # Update with file content
                    break  # If successful, break out of encoding loop
                except UnicodeDecodeError:
                    continue

            if not content:  # If we couldn't read with any encoding
                print(f"Warning: Could not decode {file_path}, using default")

        except Exception as e:
            print(f"Warning: Could not load {file_path}: {str(e)}, using default")

    return data


def clean_json_from_response(response: str) -> str:
    """Clean JSON from AI response by removing markdown and extra text"""
    return response.replace("```json", "").replace("```", "").strip()


async def transcribe_audio_with_openai(audio_bytes: bytes, filename: str) -> str:
    """Transcribe audio using OpenAI's Whisper API with 10-minute chunking"""
    try:
        # Create temporary file
        file_ext = os.path.splitext(filename)[1] if filename else ".mp3"
        temp_file_path = create_temp_audio_file(audio_bytes, file_ext)

        try:
            # Split audio into 10-minute chunks
            chunk_paths = split_audio_into_chunks(
                temp_file_path, chunk_length_minutes=10
            )

            if not chunk_paths:
                # If no chunks created (audio too short), transcribe directly
                transcription = await transcribe_with_file(temp_file_path)
                return transcription

            # Transcribe all chunks in parallel using asyncio.gather
            transcription_tasks = [
                transcribe_with_file(chunk_path) for chunk_path in chunk_paths
            ]
            transcriptions = await asyncio.gather(*transcription_tasks)

            # Clean up chunk files
            for chunk_path in chunk_paths:
                cleanup_temp_file(chunk_path)

            # Join all transcriptions
            full_transcription = " ".join(transcriptions)
            return full_transcription

        finally:
            # Clean up main temporary file
            cleanup_temp_file(temp_file_path)

    except Exception as e:
        print(f"Error in audio transcription: {str(e)}")
        raise


def split_audio_into_chunks(
    audio_file_path: str, chunk_length_minutes: int = 10
) -> list:
    """Split audio file into chunks of specified length in minutes"""
    try:
        # Load audio file
        audio = AudioSegment.from_file(audio_file_path)

        # Convert minutes to milliseconds
        chunk_length_ms = chunk_length_minutes * 60 * 1000

        # If audio is shorter than chunk length, return empty list (will use original file)
        if len(audio) <= chunk_length_ms:
            return []

        chunk_paths = []
        total_chunks = len(audio) // chunk_length_ms + (
            1 if len(audio) % chunk_length_ms > 0 else 0
        )

        print(
            f"Splitting audio into {total_chunks} chunks of {chunk_length_minutes} minutes each"
        )

        # Create temp directory if it doesn't exist
        temp_dir = "temp"
        os.makedirs(temp_dir, exist_ok=True)

        for i in range(0, len(audio), chunk_length_ms):
            chunk = audio[i : i + chunk_length_ms]

            # Create temporary file for chunk in temp directory
            chunk_file_ext = os.path.splitext(audio_file_path)[1]
            with tempfile.NamedTemporaryFile(
                delete=False, suffix=chunk_file_ext, dir=temp_dir
            ) as chunk_file:
                chunk_path = chunk_file.name

            # Export chunk to file
            chunk.export(
                chunk_path, format=chunk_file_ext[1:]
            )  # Remove the dot from extension
            chunk_paths.append(chunk_path)

        return chunk_paths

    except Exception as e:
        print(f"Error splitting audio into chunks: {str(e)}")
        raise


def create_temp_audio_file(audio_bytes: bytes, file_ext: str) -> str:
    """Create a temporary audio file in temp directory and return its path"""
    try:
        # Create temp directory if it doesn't exist
        temp_dir = "temp"
        os.makedirs(temp_dir, exist_ok=True)

        # Create temp file with proper extension in temp directory
        with tempfile.NamedTemporaryFile(
            delete=False, suffix=file_ext, dir=temp_dir
        ) as temp_file:
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
