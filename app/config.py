import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    GEMINI_API_KEY: str = ""
    UPLOAD_DIR: str = "/workspaces/resume_ats_/uploads"
    OUTPUT_DIR: str = "/workspaces/resume_ats_/output"

    class Config:
        env_file = ".env"


settings = Settings()

# Create dirs at import time so they always exist
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
os.makedirs(settings.OUTPUT_DIR, exist_ok=True)
