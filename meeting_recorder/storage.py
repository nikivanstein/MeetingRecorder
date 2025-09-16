"""Persistence helpers for saving meeting artefacts."""

from __future__ import annotations

import datetime as _dt
from pathlib import Path
from typing import Dict, Iterable

from .models import SpeakerSegment, TranscriptionResult


def ensure_directory(path: str | Path) -> Path:
    """Ensure a directory exists and return it as a :class:`Path`."""

    directory = Path(path)
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def serialise_segments(segments: Iterable[SpeakerSegment]) -> str:
    """Return a human readable representation of the transcript."""

    lines = []
    for segment in segments:
        lines.append(
            f"[{_format_ts(segment.start)}-{_format_ts(segment.end)}] {segment.speaker}: {segment.text}"
        )
    return "\n".join(lines)


def save_meeting_artifacts(
    transcript: TranscriptionResult,
    summary: Dict[str, object],
    output_dir: str | Path | None = None,
) -> Path:
    """Persist the transcript and summary into a timestamped text file."""

    directory = ensure_directory(output_dir or "meeting_outputs")
    timestamp = _dt.datetime.now(_dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    file_path = directory / f"meeting_{timestamp}.md"
    action_items = summary.get("action_items") or []
    if isinstance(action_items, list):
        action_lines = [
            f"- {item.get('description')} (Owner: {item.get('owner', 'Unassigned')})"
            for item in action_items
            if isinstance(item, dict)
        ]
    else:
        action_lines = ["- No action items"]
    content = "\n".join(
        [
            "# Meeting Transcript",
            serialise_segments(transcript.segments),
            "",
            "# Summary",
            str(summary.get("summary", "")),
            "",
            "# Action Items",
            "\n".join(action_lines) or "- No action items",
        ]
    )
    file_path.write_text(content)
    return file_path


def _format_ts(value: float) -> str:
    minutes, seconds = divmod(int(value), 60)
    return f"{minutes:02d}:{seconds:02d}"


__all__ = ["save_meeting_artifacts", "serialise_segments", "ensure_directory"]
