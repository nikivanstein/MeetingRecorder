from email.message import EmailMessage
from pathlib import Path

from meeting_recorder.models import TranscriptResult
from meeting_recorder.notifier import EmailNotifier, ResultSaver


def test_result_saver_writes_file(tmp_path):
    transcript = TranscriptResult(
        text="Hello",
        summary="Summary",
        action_items="Action items",
    )
    saver = ResultSaver()
    saved = saver.save(transcript, directory=tmp_path)
    assert Path(saved).parent == tmp_path
    with open(saved, "r", encoding="utf-8") as handle:
        contents = handle.read()
    assert "Meeting Transcript" in contents
    assert "Summary" in contents
    assert "Action Items" in contents


def test_email_notifier_sends(monkeypatch, tmp_path):
    transcript = TranscriptResult(text="Hi", summary="Sum", action_items="Act")
    notifier = EmailNotifier(
        sender="sender@example.com",
        recipient="recipient@example.com",
        smtp_server="smtp.example.com",
        smtp_port=587,
        username="user",
        password="pass",
    )

    sent_messages = {}

    class DummySMTP:
        def __init__(self, server, port):
            assert server == "smtp.example.com"
            assert port == 587

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def starttls(self):
            sent_messages["tls"] = True

        def login(self, username, password):
            sent_messages["login"] = (username, password)

        def send_message(self, message: EmailMessage):
            sent_messages["message"] = message

    monkeypatch.setattr("meeting_recorder.notifier.smtplib.SMTP", DummySMTP)

    notifier.send(transcript)
    assert sent_messages["tls"] is True
    assert sent_messages["login"] == ("user", "pass")
    assert isinstance(sent_messages["message"], EmailMessage)
