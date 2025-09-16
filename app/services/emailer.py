"""Email integration for exporting meeting summaries."""
from __future__ import annotations

import smtplib
from email.message import EmailMessage
from typing import Optional, Protocol, runtime_checkable

from ..config import EmailSettings


class EmailNotConfiguredError(RuntimeError):
    """Raised when email sending is requested but not configured."""


@runtime_checkable
class SMTPClient(Protocol):
    """Protocol describing the subset of smtplib.SMTP used by EmailSender."""

    def starttls(self) -> None:  # pragma: no cover - protocol definition
        ...

    def login(self, username: str, password: str) -> None:  # pragma: no cover
        ...

    def send_message(self, message: EmailMessage) -> None:  # pragma: no cover
        ...

    def quit(self) -> None:  # pragma: no cover
        ...


class EmailSender:
    """Utility class responsible for dispatching emails."""

    def __init__(self, settings: EmailSettings, smtp_factory=smtplib.SMTP) -> None:
        self._settings = settings
        self._smtp_factory = smtp_factory

    def _require_enabled(self) -> None:
        if not self._settings.enabled:
            raise EmailNotConfiguredError("Email sending is disabled. Set EMAIL_ENABLED=true.")
        if not self._settings.smtp_server:
            raise EmailNotConfiguredError("SMTP_SERVER must be configured for email sending.")

    def send(self, subject: str, body: str, recipient: Optional[str] = None) -> None:
        """Send an email with the supplied subject and body."""

        self._require_enabled()
        recipient = recipient or self._settings.default_recipient
        if not recipient:
            raise EmailNotConfiguredError("Recipient email is not configured.")

        sender = self._settings.default_sender or self._settings.smtp_username
        if not sender:
            raise EmailNotConfiguredError("Sender email is not configured.")

        with self._smtp_factory(self._settings.smtp_server, self._settings.smtp_port) as client:
            smtp_client: SMTPClient = client
            if self._settings.use_tls:
                smtp_client.starttls()
            if self._settings.smtp_username and self._settings.smtp_password:
                smtp_client.login(self._settings.smtp_username, self._settings.smtp_password)

            message = EmailMessage()
            message["Subject"] = subject
            message["From"] = sender
            message["To"] = recipient
            message.set_content(body)

            smtp_client.send_message(message)


__all__ = ["EmailSender", "EmailNotConfiguredError"]
