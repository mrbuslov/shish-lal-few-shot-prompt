from pydantic_settings import BaseSettings
from pydantic import Field

class Settings(BaseSettings):
    OPENAI_API_KEY: str = Field(
        ...,
        description="OpenAI API Key",
    )
    ANTHROPIC_API_KEY: str = Field(
        ...,
        description="Anthropic API Key",
    )
    
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        ignore_extra = True


settings = Settings()
