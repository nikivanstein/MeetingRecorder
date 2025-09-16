"""Dataclasses used throughout the Meeting Recorder app."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class TranscriptSegment:
    """Represents a single segment of the transcript."""

    speaker: str
    text: str
    start: Optional[float] = None
    end: Optional[float] = None


@dataclass
class TranscriptResult:
    """Structured result of the transcription step."""

    text: str
    segments: List[TranscriptSegment] = field(default_factory=list)
    summary: Optional[str] = None
    action_items: Optional[str] = None

    def as_text(self) -> str:
        """Combine segments into a readable transcript."""

        if not self.segments:
            return self.text
        lines = []
        for segment in self.segments:
            timestamp = ""
            if segment.start is not None and segment.end is not None:
                timestamp = f"[{segment.start:.2f}-{segment.end:.2f}] "
            lines.append(f"{timestamp}{segment.speaker}: {segment.text}")
        return "\n".join(lines)
