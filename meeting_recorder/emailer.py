"""Email helper for delivering meeting summaries."""

from __future__ import annotations

import smtplib
from email.message import EmailMessage
from pathlib import Path

from .config import EmailConfig


def send_email_with_summary(
    config: EmailConfig,
    subject: str,
    body: str,
    attachment: Path | None = None,
) -> None:
    """Send an email containing the meeting summary."""

    if not config.is_configured():
        raise RuntimeError("Email configuration is incomplete; cannot send message.")

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = config.from_address
    message["To"] = config.to_address
    message.set_content(body)

    if attachment is not None and attachment.exists():
        message.add_attachment(
            attachment.read_bytes(),
            maintype="text",
            subtype="markdown",
            filename=attachment.name,
        )

    with smtplib.SMTP(config.smtp_server, config.smtp_port) as smtp:
        if config.use_tls:
            smtp.starttls()
        smtp.login(config.username, config.password)
        smtp.send_message(message)


__all__ = ["send_email_with_summary"]
