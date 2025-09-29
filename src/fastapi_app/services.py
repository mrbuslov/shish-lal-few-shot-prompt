import json
import os
import traceback
from langchain_core.messages import HumanMessage, SystemMessage
from src.utils.schemas import LlmStageOutput

from src.utils.utils import (
    extract_text_from_docx,
    load_prompt_files,
    clean_json_from_response,
    transcribe_audio_with_openai,
)
from langchain_anthropic import ChatAnthropic


LLM_TEXT_PROCESSOR_OUTPUT_FORMAT = {
    name: field.description for name, field in LlmStageOutput.model_fields.items()
}

llm = ChatAnthropic(
    model="claude-sonnet-4-20250514",
    api_key=os.getenv("ANTHROPIC_API_KEY"),
    max_tokens=64_000,
)


async def process_stage_one(text: str) -> LlmStageOutput:
    """First stage of processing - extract structured data"""
    try:
        data = load_prompt_files()
        system_message = data["few_shot_prompt"].format(
            words_spelling=data["words_spelling"],
            LLM_TEXT_PROCESSOR_OUTPUT_FORMAT=LLM_TEXT_PROCESSOR_OUTPUT_FORMAT,
            few_shot_examples=data["examples"],
            important_notes=data["important_notes"],
        )
        print("Starting stage 1 processing...")
        response = await llm.ainvoke(
            [SystemMessage(content=system_message), HumanMessage(content=text)]
        )
        print("Stage 1 processing completed.")
        json_part = clean_json_from_response(response.content)
        json_data = json.loads(json_part)
        return LlmStageOutput(**json_data)
    except Exception as e:
        print(f"Error in stage 1 processing: {str(e)}")
        raise


async def process_stage_two(stage_one_output: LlmStageOutput) -> LlmStageOutput:
    try:
        prompts_data = load_prompt_files()
        final_html = prompts_data.get("output_example", "")
        for key, value in stage_one_output.model_dump().items():
            final_html = final_html.replace("{{" + key + "}}", str(value))

        print("Starting stage 2 processing...")
        system_message = f"""
        # Role
        You are a doctor assistant who checks if final report is correct up to important notes
        
        # Goal 
        Below is generated final report for my patient
        Your task is check if final report is correct up to important notes
        
        # Important notes 
        {prompts_data['important_notes']}
        
        # Output format
        {LLM_TEXT_PROCESSOR_OUTPUT_FORMAT}
        """
        response = await llm.ainvoke(
            [
                SystemMessage(content=system_message),
                HumanMessage(content=stage_one_output.model_dump_json()),
            ]
        )
        print("Stage 2 processing completed.")

        res = json.loads(clean_json_from_response(response.content))
        return LlmStageOutput(**res)

    except Exception as e:
        print(f"Error in stage 2 processing: {str(e)} {traceback.format_exc()}")
        raise


async def process_after_stage(llm_res: LlmStageOutput) -> str:
    """Takes llm output and returns html"""
    try:
        prompts_data = load_prompt_files()
        final_html = prompts_data.get("output_example", "")
        for key, value in llm_res.model_dump().items():
            if key == "letter_to_patient":
                value = [f"<p>{i}</p>" for i in value.split("\n")]
            final_html = final_html.replace("{{" + key + "}}", str(value or ""))
        return final_html
    except Exception as e:
        print(f"Error in process_after_stage: {str(e)} {traceback.format_exc()}")
        raise


async def process_single_text(
    text: str,
) -> tuple[LlmStageOutput, str]:
    """Process a single text and return HTML with JSON data"""
    # Stage 1 & 2 processing
    stage_one_result = await process_stage_one(text)
    final_llm_res = await process_stage_two(stage_one_result)
    html_text = await process_after_stage(final_llm_res)

    return final_llm_res, html_text


async def process_single_document(file_bytes: bytes, filename: str) -> str:
    """Process a single document file and return HTML"""
    # Extract text content based on file type
    if filename.lower().endswith(".txt"):
        file_content = file_bytes.decode("utf-8")
    elif filename.lower().endswith(".docx"):
        file_content = extract_text_from_docx(file_bytes)
    else:
        raise ValueError(f"Unsupported file type: {filename}")

    # Process the content
    stage_one_result = await process_stage_one(file_content)
    final_llm_res = await process_stage_two(stage_one_result)
    html_text = await process_after_stage(final_llm_res)

    return html_text


async def process_single_audio(audio_bytes: bytes, filename: str) -> str:
    """Process a single audio file and return HTML"""
    # Transcribe audio
    transcribed_text = await transcribe_audio_with_openai(audio_bytes, filename)

    # Process the transcribed content
    stage_one_result = await process_stage_one(transcribed_text)
    final_llm_res = await process_stage_two(stage_one_result)
    html_text = await process_after_stage(final_llm_res)

    return html_text
