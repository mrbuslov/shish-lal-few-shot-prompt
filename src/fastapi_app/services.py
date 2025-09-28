import json
import tempfile
import os
import time
import traceback
from typing import List
from io import BytesIO
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage
from src.utils.pdf_converter import html_to_pdf
from src.utils.pdf_converter.schemas import FileData
from dotenv import load_dotenv
from openai import AsyncOpenAI
from docx import Document
from bs4 import BeautifulSoup


# Load environment variables
load_dotenv()

openai_client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
model = ChatAnthropic(
    model="claude-sonnet-4-20250514",
    api_key=os.getenv("ANTHROPIC_API_KEY"),
    max_tokens=64_000,
)
OUTPUT_FORMAT = {
    "recipients_info": "str",
    "diagnosis": "str",
    "corrected_visual_acuity_right": "str",
    "corrected_visual_acuity_left": "str",
    "intraocular_pressure_right": "str",
    "intraocular_pressure_left": "str",
    "next_review": "str",
    "letter_to_patient": ["paragraph1", "paragraph2", "paragraph3"],
}


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


def extract_text_from_html(html_content: str) -> str:
    """Extract text from HTML content using BeautifulSoup"""
    try:
        soup = BeautifulSoup(html_content, "html.parser")

        # Get text and clean it up
        text = soup.get_text()
        lines = [line.strip() for line in text.splitlines()]
        return "\n".join(line for line in lines if line)
    except Exception as e:
        print(f"Error extracting text from HTML: {str(e)}")
        raise


def create_zip_archive(files: List[FileData]) -> bytes:
    """Create a ZIP archive from a list of FileData objects"""
    import zipfile

    zip_buffer = BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for file_data in files:
            zip_file.writestr(file_data.path_name, file_data.file_bytes)

    return zip_buffer.getvalue()


def load_prompt_files() -> dict:
    """Load all required prompt files"""
    base_path = "files/prompts-default"
    files = {
        "few_shot_prompt": f"{base_path}/few-shot-prompt.md",
        "examples": f"{base_path}/examples.json",
        "important_notes": f"{base_path}/important_notes.md",
        "output_example": f"{base_path}/output_example.html",
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


async def process_stage_one(text: str) -> str:
    """First stage of processing - extract structured data"""
    try:
        data = load_prompt_files()
        user_message = (
            f"# FEW-SHOT PROMPT:\n\n{data['few_shot_prompt']}\n\n"
            f"# OUTPUT FORMAT (return ONLY valid JSON):\n\n{json.dumps(OUTPUT_FORMAT, indent=2)}\n\n"
            f"# TEXT TO ANALYZE:\n\n{text}\n\n"
            f"# EXAMPLES FOR REFERENCE:\n\n{data['examples']}"
        )
        print("Starting stage 1 processing...")
        response = model.invoke([HumanMessage(content=user_message)])
        print("Stage 1 processing completed.")
        return response.content
    except Exception as e:
        print(f"Error in stage 1 processing: {str(e)}")
        raise


def clean_json_from_response(response: str) -> str:
    """Clean JSON from AI response by removing markdown and extra text"""
    response = response.strip()

    # Remove markdown code blocks
    if response.startswith("```json"):
        response = response[7:]
    elif response.startswith("```"):
        response = response[3:]

    if response.endswith("```"):
        response = response[:-3]

    response = response.strip()

    # Find JSON content between braces
    start_idx = response.find("{")
    end_idx = response.rfind("}")

    if start_idx != -1 and end_idx != -1 and start_idx < end_idx:
        response = response[start_idx : end_idx + 1]

    return response.strip()


async def process_stage_two(stage_one_output: str) -> tuple[str, dict]:
    try:
        prompts_data = load_prompt_files()
        load_prompt_files()
        json_part = clean_json_from_response(stage_one_output)
        json_data = json.loads(json_part)
        for key in OUTPUT_FORMAT:
            if key not in json_data:
                json_data[key] = ""

        # Format the letter_to_patient for HTML output
        if isinstance(json_data.get("letter_to_patient"), list):
            json_data["letter_to_patient"] = "\n".join(
                [
                    f'<p style="text-align:justify; font-size:10pt"><span style="font-family:Arial">{paragraph}</span></p>'
                    for paragraph in json_data["letter_to_patient"]
                ]
            )

        # Generate HTML from template
        html_template = prompts_data.get("output_example", "")
        final_html = html_template
        for key, value in json_data.items():
            final_html = final_html.replace("{{" + key + "}}", str(value))

        print("Stage 2 processing completed.")

        # Parse back to get clean JSON for return
        clean_json_data = json.loads(json_part)

        return final_html, clean_json_data

    except Exception as e:
        print(f"Error in stage 2 processing: {str(e)} {traceback.format_exc()}")
        raise


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
                model="whisper-1", file=audio_file, response_format="text"
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


# Main wrapper functions
async def process_single_text(
    text: str, filename: str = "processed_document.docx"
) -> tuple[FileData, dict]:
    """Process a single text and return FileData with JSON data"""
    # Stage 1 & 2 processing
    stage_one_result = await process_stage_one(text)
    final_result, json_res = await process_stage_two(stage_one_result)

    # Convert to PDF format using local converter
    conversion_result = html_to_pdf(final_result, filename.replace(".docx", ".pdf"))
    file_data = FileData.from_conversion_result(conversion_result)
    return file_data, json_res


async def process_single_document(file_bytes: bytes, filename: str) -> FileData:
    """Process a single document file and return FileData"""
    # Extract text content based on file type
    if filename.lower().endswith(".txt"):
        file_content = file_bytes.decode("utf-8")
    elif filename.lower().endswith(".html"):
        html_content = file_bytes.decode("utf-8")
        file_content = extract_text_from_html(html_content)
    elif filename.lower().endswith(".docx"):
        file_content = extract_text_from_docx(file_bytes)
    else:
        raise ValueError(f"Unsupported file type: {filename}")

    # Process the content
    stage_one_result = await process_stage_one(file_content)
    final_result, _ = await process_stage_two(stage_one_result)

    # Convert to PDF format using local converter
    output_filename = f"processed_{filename.rsplit('.', 1)[0]}.pdf"
    conversion_result = html_to_pdf(final_result, output_filename)
    file_data = FileData.from_conversion_result(conversion_result)
    return file_data


async def process_single_audio(audio_bytes: bytes, filename: str) -> FileData:
    """Process a single audio file and return FileData"""
    # Transcribe audio
    transcribed_text = await transcribe_audio_with_openai(audio_bytes, filename)

    # Process the transcribed content
    stage_one_result = await process_stage_one(transcribed_text)
    final_result, _ = await process_stage_two(stage_one_result)

    # Convert to PDF format using local converter
    output_filename = f"processed_{filename.rsplit('.', 1)[0]}.pdf"
    conversion_result = html_to_pdf(final_result, output_filename)
    file_data = FileData.from_conversion_result(conversion_result)
    return file_data
