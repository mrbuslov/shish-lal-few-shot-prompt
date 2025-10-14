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
    IS_DEBUG: bool = Field(
        default=False,
        description="Debug mode flag",
    )
    AUTH_SUPERADMIN_EMAIL: str = Field(
        ...,
        description="Superadmin email for authentication",
    )
    AUTH_SUPERADMIN_PASSWORD: str = Field(
        ...,
        description="Superadmin password for authentication",
    )
    MONGODB_URL: str = Field(
        ...,
        description="MongoDB connection URL",
    )
    MONGODB_DB_NAME: str = Field(
        ...,
        description="MongoDB database name",
    )

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


settings = Settings()
