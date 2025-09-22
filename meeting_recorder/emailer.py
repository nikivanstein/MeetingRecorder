"""Email helper supporting optional SMTP delivery."""

from __future__ import annotations

import os
import smtplib
from dataclasses import dataclass
from email.message import EmailMessage
from pathlib import Path
from typing import Optional


@dataclass
class EmailConfig:
    """Settings required for sending meeting notes via email."""

    host: str
    port: int
    username: Optional[str]
    password: Optional[str]
    sender: str
    recipient: str
    use_tls: bool = True

    @classmethod
    def from_env(cls) -> Optional["EmailConfig"]:
        host = os.environ.get("SMTP_HOST")
        sender = os.environ.get("EMAIL_SENDER")
        recipient = os.environ.get("MEETING_EMAIL_RECIPIENT") or os.environ.get("EMAIL_RECIPIENT")
        if not (host and sender and recipient):
            return None
        port = int(os.environ.get("SMTP_PORT", "587"))
        username = os.environ.get("SMTP_USERNAME")
        password = os.environ.get("SMTP_PASSWORD")
        use_tls = os.environ.get("SMTP_USE_TLS", "true").lower() in {"1", "true", "yes"}
        return cls(
            host=host,
            port=port,
            username=username,
            password=password,
            sender=sender,
            recipient=recipient,
            use_tls=use_tls,
        )


class EmailClient:
    """SMTP based email sender used by the application."""

    def __init__(self, config: EmailConfig) -> None:
        self.config = config

    @classmethod
    def from_env(cls) -> Optional["EmailClient"]:
        config = EmailConfig.from_env()
        if not config:
            return None
        return cls(config)

    def send(self, subject: str, body: str, attachment: Path | None = None) -> None:
        message = EmailMessage()
        message["Subject"] = subject
        message["From"] = self.config.sender
        message["To"] = self.config.recipient
        message.set_content(body)
        if attachment and attachment.exists():
            message.add_attachment(
                attachment.read_bytes(),
                maintype="text",
                subtype="markdown",
                filename=attachment.name,
            )
        if self.config.use_tls:
            with smtplib.SMTP(self.config.host, self.config.port) as smtp:
                smtp.starttls()
                if self.config.username and self.config.password:
                    smtp.login(self.config.username, self.config.password)
                smtp.send_message(message)
        else:  # pragma: no cover - rarely used branch
            with smtplib.SMTP(self.config.host, self.config.port) as smtp:
                if self.config.username and self.config.password:
                    smtp.login(self.config.username, self.config.password)
                smtp.send_message(message)


__all__ = ["EmailClient", "EmailConfig"]
