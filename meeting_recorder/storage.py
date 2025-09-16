"""Persisting meeting outputs to disk."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from .summarizer import MeetingSummary
from .transcription import TranscriptionResult


def build_default_filename(prefix: str = "meeting") -> str:
    """Return a timestamped file name."""

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    return f"{prefix}-{timestamp}.md"


def render_meeting_markdown(
    transcription: TranscriptionResult, summary: MeetingSummary
) -> str:
    """Combine all meeting data into a single Markdown string."""

    parts = ["# Meeting Notes", ""]
    parts.append(summary.format_markdown())
    parts.append("")
    parts.append(transcription.format_markdown())
    return "\n".join(parts)


def save_meeting_result(
    transcription: TranscriptionResult,
    summary: MeetingSummary,
    output_dir: Path,
    filename: str | None = None,
) -> Path:
    """Persist the meeting transcript and summary in *output_dir*."""

    output_dir.mkdir(parents=True, exist_ok=True)
    file_name = filename or build_default_filename()
    file_path = output_dir / file_name
    markdown = render_meeting_markdown(transcription, summary)
    file_path.write_text(markdown, encoding="utf-8")
    return file_path


__all__ = [
    "build_default_filename",
    "render_meeting_markdown",
    "save_meeting_result",
]
