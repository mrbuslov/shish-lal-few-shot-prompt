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
    transcribe_audio_with_openai,
    load_default_prompt_files_data,
)

llm = ChatAnthropic(
    model="claude-sonnet-4-20250514",
    api_key=settings.ANTHROPIC_API_KEY,
    max_tokens=64_000,
)

structured_llm = llm.with_structured_output(LlmStageOutput)



async def process_stage_one(text: str, user_id: str = None, additional_prompt: str = None) -> LlmStageOutput:
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
        
        # Prepare system message
        format_data = {
            "words_spelling": data["words_spelling"],
            "few_shot_examples": data["examples"],
            "important_notes": data["important_notes"],
        }
        system_message = data["few_shot_prompt"]
        for key, value in format_data.items():
            system_message = system_message.replace("{" + key + "}", value)
        
        # Add additional prompt if provided
        if additional_prompt:
            system_message += f"\n\nAdditional Instructions: {additional_prompt}"
        
        print("Starting stage 1 processing...")
        response = await structured_llm.ainvoke(
            [SystemMessage(content=system_message), HumanMessage(content=text)],
        )
        print("Stage 1 output:", response)
        print("Stage 1 processing completed.")
        return response
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
        Note: patient letter must not have any other fields content, only letter content
        
        # Important notes 
        {json.dumps(prompts_data['important_notes'])}
        """
        response = await structured_llm.ainvoke(
            [
                SystemMessage(content=system_message),
                HumanMessage(content=stage_one_output.model_dump_json()),
            ]
        )
        print("Stage 2 output:", response)
        print("Stage 2 processing completed.")
        return response

    except Exception as e:
        print(f"Error in stage 2 processing: {str(e)} {traceback.format_exc()}")
        raise


async def process_single_text(text: str, user_id: str = None, additional_prompt: str = None,) -> LlmStageOutput:
    """Process a single text and return LlmStageOutput"""
    # Stage 1 & 2 processing
    stage_one_result = await process_stage_one(text, user_id, additional_prompt)
    final_llm_res = await process_stage_two(stage_one_result, user_id)
    final_llm_res_dict = final_llm_res.model_dump()
    for key, value in final_llm_res_dict.items():
        if value is None:
            final_llm_res_dict[key] = "_"
    return LlmStageOutput(**final_llm_res_dict)


async def transcribe_single_audio(audio_bytes: bytes, filename: str) -> str:
    """Transcribe a single audio file and return the transcribed text"""
    transcribed_text = await transcribe_audio_with_openai(audio_bytes, filename)
    print(f"Transcribed text: {transcribed_text}")
    return transcribed_text
