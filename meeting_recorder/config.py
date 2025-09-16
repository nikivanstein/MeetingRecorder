"""Configuration helpers for the Meeting Recorder application."""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from typing import Optional


@dataclass
class Settings:
    """Container for environment driven configuration values."""

    assemblyai_api_key: Optional[str] = None
    openai_api_key: Optional[str] = None
    ollama_endpoint: Optional[str] = None
    email_sender: Optional[str] = None
    email_recipient: Optional[str] = None
    smtp_server: str = "localhost"
    smtp_port: int = 25
    smtp_username: Optional[str] = None
    smtp_password: Optional[str] = None


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the application settings loaded from environment variables."""

    return Settings(
        assemblyai_api_key=os.getenv("ASSEMBLYAI_API_KEY"),
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        ollama_endpoint=os.getenv("OLLAMA_ENDPOINT"),
        email_sender=os.getenv("MEETING_EMAIL_SENDER"),
        email_recipient=os.getenv("MEETING_EMAIL_RECIPIENT"),
        smtp_server=os.getenv("MEETING_SMTP_SERVER", "localhost"),
        smtp_port=int(os.getenv("MEETING_SMTP_PORT", "25")),
        smtp_username=os.getenv("MEETING_SMTP_USERNAME"),
        smtp_password=os.getenv("MEETING_SMTP_PASSWORD"),
    )
