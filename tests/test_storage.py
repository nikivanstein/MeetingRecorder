"""Tests for persisting meeting notes to disk."""

from pathlib import Path

from meeting_recorder.storage import build_default_filename, render_meeting_markdown, save_meeting_result
from meeting_recorder.summarizer import MeetingSummary
from meeting_recorder.transcription import TranscriptionResult, Utterance


def test_build_default_filename_generates_markdown_name() -> None:
    filename = build_default_filename("demo")
    assert filename.startswith("demo-")
    assert filename.endswith(".md")


def _sample_transcription() -> TranscriptionResult:
    return TranscriptionResult(
        text="Alice greeted Bob.",
        utterances=[Utterance(speaker="Alice", text="Hello Bob", start=0, end=1000)],
    )


def _sample_summary() -> MeetingSummary:
    return MeetingSummary(summary="Discussed project kickoff", action_items=["Email the plan"])


def test_render_meeting_markdown_contains_sections() -> None:
    markdown = render_meeting_markdown(_sample_transcription(), _sample_summary())
    assert "# Meeting Notes" in markdown
    assert "## Summary" in markdown
    assert "## Transcript" in markdown
    assert "Alice" in markdown


def test_save_meeting_result_creates_file(tmp_path: Path) -> None:
    path = save_meeting_result(_sample_transcription(), _sample_summary(), tmp_path)
    assert path.exists()
    contents = path.read_text(encoding="utf-8")
    assert "Meeting Notes" in contents
    assert "Email the plan" in contents
