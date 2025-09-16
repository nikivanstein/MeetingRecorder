"""Configuration helpers for the Meeting Recorder app."""

from __future__ import annotations

from dataclasses import dataclass, field
import os
from pathlib import Path
from typing import Optional


@dataclass(slots=True)
class EmailConfig:
    """Configuration required to send meeting summaries via email."""

    smtp_server: Optional[str] = None
    smtp_port: Optional[int] = None
    username: Optional[str] = None
    password: Optional[str] = None
    from_address: Optional[str] = None
    to_address: Optional[str] = None
    use_tls: bool = True

    def is_configured(self) -> bool:
        """Return ``True`` when all required fields are configured."""

        required_fields = [
            self.smtp_server,
            self.smtp_port,
            self.username,
            self.password,
            self.from_address,
            self.to_address,
        ]
        return all(field not in (None, "") for field in required_fields)


@dataclass(slots=True)
class AppConfig:
    """Application configuration read from environment variables."""

    assemblyai_api_key: Optional[str] = None
    openai_api_key: Optional[str] = None
    openai_model: str = "gpt-3.5-turbo"
    ollama_model: Optional[str] = None
    output_dir: Path = Path("meeting_outputs")
    email: EmailConfig = field(default_factory=EmailConfig)

    @classmethod
    def from_env(cls) -> "AppConfig":
        """Create an :class:`AppConfig` using environment variables."""

        output_dir = Path(os.getenv("MEETING_OUTPUT_DIR", "meeting_outputs"))
        email_config = EmailConfig(
            smtp_server=os.getenv("EMAIL_SMTP_SERVER"),
            smtp_port=int(os.getenv("EMAIL_SMTP_PORT", "0")) or None,
            username=os.getenv("EMAIL_USERNAME"),
            password=os.getenv("EMAIL_PASSWORD"),
            from_address=os.getenv("EMAIL_FROM_ADDRESS"),
            to_address=os.getenv("EMAIL_TO_ADDRESS"),
            use_tls=os.getenv("EMAIL_USE_TLS", "true").lower() != "false",
        )

        return cls(
            assemblyai_api_key=os.getenv("ASSEMBLYAI_API_KEY"),
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            openai_model=os.getenv("OPENAI_MODEL", "gpt-3.5-turbo"),
            ollama_model=os.getenv("OLLAMA_MODEL"),
            output_dir=output_dir,
            email=email_config,
        )


__all__ = ["EmailConfig", "AppConfig"]
