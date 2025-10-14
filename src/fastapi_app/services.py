import json
import os
import traceback
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_anthropic import ChatAnthropic

from src.common.settings import settings
from src.common.models import User
from src.common.db_facade import DatabaseFacade
from src.utils.schemas import LlmStageOutput
from src.utils.utils import (
    extract_text_from_docx,
    load_prompt_files,
    clean_json_from_response,
    transcribe_audio_with_openai,
    load_default_prompt_files_data,
)


LLM_TEXT_PROCESSOR_OUTPUT_FORMAT = {
    name: field.description for name, field in LlmStageOutput.model_fields.items()
}

llm = ChatAnthropic(
    model="claude-sonnet-4-20250514",
    api_key=settings.ANTHROPIC_API_KEY,
    max_tokens=64_000,
)


async def process_stage_one(text: str, user_id: str = None) -> LlmStageOutput:
    """First stage of processing - extract structured data"""
    try:
        # Try to use specific user's data if user_id provided
        if user_id:
            try:
                data = await load_prompt_files(user_id)
            except Exception:
                # If user-specific data fails, fallback to superadmin or default
                try:
                    user_facade = DatabaseFacade(User)
                    superadmin = await user_facade.get_one(is_superuser=True)
                    if superadmin:
                        data = await load_prompt_files(str(superadmin.id))
                    else:
                        data = load_default_prompt_files_data()
                except Exception:
                    data = load_default_prompt_files_data()
        else:
            # Fallback behavior when no user_id provided
            try:
                user_facade = DatabaseFacade(User)
                superadmin = await user_facade.get_one(is_superuser=True)
                if superadmin:
                    data = await load_prompt_files(str(superadmin.id))
                else:
                    data = load_default_prompt_files_data()
            except Exception:
                # Fallback to default data if MongoDB is not available
                data = load_default_prompt_files_data()
        system_message = data["few_shot_prompt"].format(
            words_spelling=data["words_spelling"],
            LLM_TEXT_PROCESSOR_OUTPUT_FORMAT=json.dumps(
                LLM_TEXT_PROCESSOR_OUTPUT_FORMAT
            ),
            few_shot_examples=data["examples"],
            important_notes=data["important_notes"],
        )
        print("Starting stage 1 processing...")
        response = await llm.ainvoke(
            [SystemMessage(content=system_message), HumanMessage(content=text)],
        )
        print(response.content)
        print("Stage 1 processing completed.")
        json_data = json.loads(clean_json_from_response(response.content))
        return LlmStageOutput(**json_data)
    except Exception as e:
        print(f"Error in stage 1 processing: {str(e)}")
        raise


async def process_stage_two(
    stage_one_output: LlmStageOutput, user_id: str = None
) -> LlmStageOutput:
    try:
        # Try to use specific user's data if user_id provided
        if user_id:
            try:
                prompts_data = await load_prompt_files(user_id)
            except Exception:
                # If user-specific data fails, fallback to superadmin or default
                try:
                    user_facade = DatabaseFacade(User)
                    superadmin = await user_facade.get_one(is_superuser=True)
                    if superadmin:
                        prompts_data = await load_prompt_files(str(superadmin.id))
                    else:
                        prompts_data = load_default_prompt_files_data()
                except Exception:
                    prompts_data = load_default_prompt_files_data()
        else:
            # Fallback behavior when no user_id provided
            try:
                user_facade = DatabaseFacade(User)
                superadmin = await user_facade.get_one(is_superuser=True)
                if superadmin:
                    prompts_data = await load_prompt_files(str(superadmin.id))
                else:
                    prompts_data = load_default_prompt_files_data()
            except Exception:
                # Fallback to default data if MongoDB is not available
                prompts_data = load_default_prompt_files_data()

        print("Starting stage 2 processing...")
        system_message = f"""
        # Role
        You are a doctor assistant who checks if final report is correct up to important notes
        
        # Goal 
        Below is generated final report for my patient
        Your task is check if final report is correct up to important notes
        Return JSON with fixed fields. If nothing to fix, return as it is. Do not write anything else.
        
        # Important notes 
        {json.dumps(prompts_data['important_notes'])}
        
        # Output format
        {json.dumps(LLM_TEXT_PROCESSOR_OUTPUT_FORMAT)}
        """
        response = await llm.ainvoke(
            [
                SystemMessage(content=system_message),
                HumanMessage(content=stage_one_output.model_dump_json()),
            ]
        )
        print(response.content)
        print("Stage 2 processing completed.")

        res = json.loads(clean_json_from_response(response.content))
        return LlmStageOutput(**res)

    except Exception as e:
        print(f"Error in stage 2 processing: {str(e)} {traceback.format_exc()}")
        raise


async def process_single_text(text: str, user_id: str = None) -> LlmStageOutput:
    """Process a single text and return LlmStageOutput"""
    # Stage 1 & 2 processing
    stage_one_result = await process_stage_one(text, user_id)
    final_llm_res = await process_stage_two(stage_one_result, user_id)
    final_llm_res.source_text = text
    return final_llm_res


async def process_single_document(
    file_bytes: bytes, filename: str, user_id: str = None
) -> LlmStageOutput:
    """Process a single document file and return LlmStageOutput"""
    # Extract text content based on file type
    if filename.lower().endswith(".txt"):
        file_content = file_bytes.decode("utf-8")
    elif filename.lower().endswith(".docx"):
        file_content = extract_text_from_docx(file_bytes)
    else:
        raise ValueError(f"Unsupported file type: {filename}")

    # Process the content
    stage_one_result = await process_stage_one(file_content, user_id)
    final_llm_res = await process_stage_two(stage_one_result, user_id)
    final_llm_res.source_text = file_content
    return final_llm_res


async def process_single_audio(
    audio_bytes: bytes, filename: str, user_id: str = None
) -> LlmStageOutput:
    """Process a single audio file and return LlmStageOutput"""
    # Transcribe audio
    transcribed_text = await transcribe_audio_with_openai(audio_bytes, filename)
    print(f"Transcribed text: {transcribed_text}")

    # Process the transcribed content
    stage_one_result = await process_stage_one(transcribed_text, user_id)
    final_llm_res = await process_stage_two(stage_one_result, user_id)
    final_llm_res.source_text = transcribed_text
    return final_llm_res
