"""Unit tests for the email sender."""
from __future__ import annotations

from email.message import EmailMessage

import pytest

from app.config import EmailSettings
from app.services.emailer import EmailNotConfiguredError, EmailSender


class DummySMTP:
    """Simple SMTP stub that records interactions."""

    def __init__(self, server: str, port: int) -> None:
        self.server = server
        self.port = port
        self.started_tls = False
        self.login_credentials: tuple[str, str] | None = None
        self.messages: list[EmailMessage] = []

    def __enter__(self) -> "DummySMTP":  # pragma: no cover - simple context manager
        return self

    def __exit__(self, exc_type, exc, tb) -> None:  # pragma: no cover
        return None

    def starttls(self) -> None:
        self.started_tls = True

    def login(self, username: str, password: str) -> None:
        self.login_credentials = (username, password)

    def send_message(self, message: EmailMessage) -> None:
        self.messages.append(message)

    def quit(self) -> None:  # pragma: no cover - smtplib compat
        return None


def test_email_sender_dispatches_message() -> None:
    settings = EmailSettings(
        enabled=True,
        smtp_server="smtp.test",
        smtp_port=587,
        smtp_username="user@test",
        smtp_password="secret",
        use_tls=True,
        default_sender="noreply@test",
        default_recipient="recipient@test",
    )

    instances: list[DummySMTP] = []

    def factory(server: str, port: int) -> DummySMTP:
        instance = DummySMTP(server, port)
        instances.append(instance)
        return instance

    sender = EmailSender(settings, smtp_factory=factory)
    sender.send("Subject", "Body text")

    assert instances, "Expected factory to be called"
    smtp = instances[0]
    assert smtp.server == "smtp.test"
    assert smtp.started_tls is True
    assert smtp.login_credentials == ("user@test", "secret")
    assert smtp.messages and smtp.messages[0]["To"] == "recipient@test"


def test_email_sender_requires_configuration() -> None:
    settings = EmailSettings(
        enabled=False,
        smtp_server=None,
        default_sender=None,
        default_recipient=None,
    )

    sender = EmailSender(settings, smtp_factory=lambda *_args, **_kwargs: DummySMTP("", 0))

    with pytest.raises(EmailNotConfiguredError):
        sender.send("Subject", "Body")
