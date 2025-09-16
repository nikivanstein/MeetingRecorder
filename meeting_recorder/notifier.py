"""Persistence and notification helpers."""

from __future__ import annotations

import os
import smtplib
import tempfile
from datetime import datetime
from email.message import EmailMessage
from typing import Optional

from .models import TranscriptResult


class ResultSaver:
    """Save meeting outputs to disk."""

    def save(self, transcript: TranscriptResult, directory: Optional[str] = None) -> str:
        """Persist the transcript, summary and action items to a text file."""

        directory = directory or tempfile.gettempdir()
        os.makedirs(directory, exist_ok=True)
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        file_path = os.path.join(directory, f"meeting_notes_{timestamp}.txt")
        with open(file_path, "w", encoding="utf-8") as handle:
            handle.write("# Meeting Transcript\n\n")
            handle.write(transcript.as_text() or transcript.text)
            handle.write("\n\n# Summary\n\n")
            handle.write(transcript.summary or "Not available")
            handle.write("\n\n# Action Items\n\n")
            handle.write(transcript.action_items or "Not available")
        return file_path


class EmailNotifier:
    """Send the meeting outputs to a preset email address."""

    def __init__(
        self,
        sender: str,
        recipient: str,
        smtp_server: str,
        smtp_port: int,
        username: Optional[str] = None,
        password: Optional[str] = None,
    ) -> None:
        if not sender or not recipient:
            raise ValueError("Sender and recipient email addresses are required")
        self.sender = sender
        self.recipient = recipient
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.username = username
        self.password = password

    def send(self, transcript: TranscriptResult, attachment_path: Optional[str] = None) -> None:
        """Send the meeting summary via email."""

        message = EmailMessage()
        message["From"] = self.sender
        message["To"] = self.recipient
        message["Subject"] = "Meeting summary"
        body = (
            f"Summary:\n{transcript.summary or 'Not available'}\n\n"
            f"Action Items:\n{transcript.action_items or 'Not available'}\n"
        )
        message.set_content(body)

        if attachment_path and os.path.exists(attachment_path):
            with open(attachment_path, "rb") as handle:
                data = handle.read()
            message.add_attachment(
                data,
                maintype="text",
                subtype="plain",
                filename=os.path.basename(attachment_path),
            )

        with smtplib.SMTP(self.smtp_server, self.smtp_port) as smtp:
            if self.username and self.password:
                smtp.starttls()
                smtp.login(self.username, self.password)
            smtp.send_message(message)
