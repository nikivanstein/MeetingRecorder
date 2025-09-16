"""Data models used by the meeting recorder app."""

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Dict, List, Sequence


@dataclass
class SpeakerSegment:
    """Represents a diarised chunk of audio."""

    speaker: str
    start: float
    end: float
    text: str

    def to_labelled(self, labels: Dict[str, str] | None = None) -> "SpeakerSegment":
        """Return a copy of the segment with the speaker replaced by custom labels."""

        label_map = labels or {}
        labelled = label_map.get(self.speaker, self.speaker)
        return SpeakerSegment(speaker=labelled, start=self.start, end=self.end, text=self.text)


@dataclass
class TranscriptionResult:
    """Collection of diarised segments and convenience helpers."""

    segments: Sequence[SpeakerSegment]

    @property
    def text(self) -> str:
        """Return the concatenated transcript text."""

        return "\n".join(segment.text for segment in self.segments)

    def apply_labels(self, labels: Dict[str, str] | None) -> "TranscriptionResult":
        """Return a new result with speaker labels applied."""

        labelled_segments = [segment.to_labelled(labels) for segment in self.segments]
        return TranscriptionResult(segments=labelled_segments)

    def to_payload(self) -> Dict[str, List[Dict[str, float | str]]]:
        """Serialize the result into a JSON-serialisable payload."""

        return {
            "segments": [asdict(segment) for segment in self.segments],
            "text": self.text,
        }

    @classmethod
    def from_payload(cls, payload: Dict[str, List[Dict[str, float | str]]]) -> "TranscriptionResult":
        """Rehydrate a transcription result from :meth:`to_payload` output."""

        segments = [
            SpeakerSegment(
                speaker=item["speaker"],
                start=float(item["start"]),
                end=float(item["end"]),
                text=str(item["text"]),
            )
            for item in payload.get("segments", [])
        ]
        return cls(segments=segments)
