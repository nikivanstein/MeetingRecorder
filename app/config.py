"""Application configuration utilities."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Optional


def _bool_env(var_name: str, default: bool = False) -> bool:
    """Return the boolean value of an environment variable."""
    value = os.getenv(var_name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass
class EmailSettings:
    """Configuration for the optional email integration."""

    enabled: bool = field(default_factory=lambda: _bool_env("EMAIL_ENABLED", False))
    smtp_server: Optional[str] = field(default_factory=lambda: os.getenv("SMTP_SERVER"))
    smtp_port: int = field(default_factory=lambda: int(os.getenv("SMTP_PORT", "587")))
    smtp_username: Optional[str] = field(default_factory=lambda: os.getenv("SMTP_USERNAME"))
    smtp_password: Optional[str] = field(default_factory=lambda: os.getenv("SMTP_PASSWORD"))
    use_tls: bool = field(default_factory=lambda: _bool_env("SMTP_USE_TLS", True))
    default_sender: Optional[str] = field(default_factory=lambda: os.getenv("EMAIL_SENDER"))
    default_recipient: Optional[str] = field(default_factory=lambda: os.getenv("EMAIL_RECIPIENT"))


@dataclass
class Settings:
    """Container for configuration loaded from environment variables."""

    assemblyai_api_key: Optional[str] = field(default_factory=lambda: os.getenv("ASSEMBLYAI_API_KEY"))
    openai_api_key: Optional[str] = field(default_factory=lambda: os.getenv("OPENAI_API_KEY"))
    openai_model: str = field(default_factory=lambda: os.getenv("OPENAI_MODEL", "gpt-4o-mini"))
    email: EmailSettings = field(default_factory=EmailSettings)


settings = Settings()

__all__ = ["settings", "Settings", "EmailSettings"]
