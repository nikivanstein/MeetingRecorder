"""Helper utilities for shaping transcription and summary output."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from typing import Iterable, Mapping, Sequence

from .transcription import TranscriptionSegment


@dataclass(frozen=True)
class RenderedSegment:
    """Lightweight representation of a transcript line."""

    timestamp: str
    speaker: str
    text: str


def format_timestamp(seconds: float) -> str:
    """Format a float number of seconds into HH:MM:SS."""

    return str(timedelta(seconds=int(seconds)))


def apply_speaker_overrides(
    segments: Iterable[TranscriptionSegment],
    overrides: Mapping[str, str] | None = None,
) -> list[RenderedSegment]:
    """Apply speaker overrides to transcript segments and render them."""

    rendered: list[RenderedSegment] = []
    overrides = overrides or {}
    for segment in segments:
        speaker = overrides.get(segment.speaker, segment.speaker)
        rendered.append(
            RenderedSegment(
                timestamp=format_timestamp(segment.start),
                speaker=speaker,
                text=segment.text,
            )
        )
    return rendered


def format_transcript_text(
    segments: Sequence[TranscriptionSegment],
    overrides: Mapping[str, str] | None = None,
) -> str:
    """Build a human readable transcript string."""

    lines = [
        f"[{rendered.timestamp}] {rendered.speaker}: {rendered.text}"
        for rendered in apply_speaker_overrides(segments, overrides)
    ]
    return "\n".join(lines).strip()


def build_result_document(
    summary: str,
    action_items: Sequence[str],
    segments: Sequence[TranscriptionSegment],
    overrides: Mapping[str, str] | None = None,
) -> str:
    """Generate a text document containing summary, actions and transcript."""

    transcript_body = format_transcript_text(segments, overrides)

    parts = ["Meeting Summary", "==============", summary.strip() or "(No summary provided)"]

    parts.extend(["", "Action Items", "============"])
    if action_items:
        parts.extend([f"- {item}" for item in action_items])
    else:
        parts.append("(No action items recorded)")

    parts.extend(["", "Transcript", "==========", transcript_body or "(No transcript available)"])
    return "\n".join(parts).strip() + "\n"


__all__ = [
    "RenderedSegment",
    "apply_speaker_overrides",
    "build_result_document",
    "format_timestamp",
    "format_transcript_text",
]
