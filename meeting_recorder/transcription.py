"""Utilities to transcribe audio using AssemblyAI with speaker diarisation."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from typing import Dict, List, Optional

try:  # pragma: no cover - optional dependency when running tests
    import assemblyai as aai
except Exception as exc:  # pragma: no cover - import error handled at runtime
    aai = None  # type: ignore
    _ASSEMBLYAI_IMPORT_ERROR = exc
else:  # pragma: no cover - executed in production environments
    _ASSEMBLYAI_IMPORT_ERROR = None

from .config import AppConfig


@dataclass(slots=True)
class Utterance:
    """A single utterance in the meeting transcript."""

    speaker: str
    text: str
    start: float
    end: float


@dataclass(slots=True)
class TranscriptionResult:
    """Container with both the full transcript and diarised utterances."""

    text: str
    utterances: List[Utterance]

    def format_markdown(self) -> str:
        """Return a Markdown representation of the transcript."""

        lines: List[str] = ["## Transcript"]
        for utterance in self.utterances:
            start = format_timestamp(utterance.start)
            lines.append(f"**{utterance.speaker} [{start}]**: {utterance.text}")
        if not self.utterances:
            lines.append(self.text)
        return "\n\n".join(lines)


def format_timestamp(milliseconds: float) -> str:
    """Convert a timestamp in milliseconds to ``HH:MM:SS`` format."""

    total_seconds = int(milliseconds / 1000)
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


def parse_speaker_labels(raw_value: Optional[str]) -> Dict[str, str]:
    """Parse user supplied speaker labels into a mapping."""

    mapping: Dict[str, str] = {}
    if not raw_value:
        return mapping

    entries = re.split(r"[\n,;]+", raw_value)
    for entry in entries:
        if not entry.strip():
            continue
        if "=" in entry:
            key, value = entry.split("=", 1)
        elif ":" in entry:
            key, value = entry.split(":", 1)
        else:
            continue
        mapping[key.strip().lower()] = value.strip()
    return mapping


def apply_speaker_labels(speaker: str | None, mapping: Dict[str, str]) -> str:
    """Return the human friendly speaker label if available."""

    normalized_key = (speaker or "").strip().lower()
    if normalized_key in mapping:
        return mapping[normalized_key]
    # AssemblyAI uses numeric or alphabetic identifiers. Present a nicer default.
    return f"Speaker {speaker}" if speaker else "Speaker"


def transcribe_audio(
    audio_path: Path | str,
    config: AppConfig,
    speaker_labels: Optional[Dict[str, str]] = None,
) -> TranscriptionResult:
    """Transcribe *audio_path* using AssemblyAI and diarisation."""

    if not config.assemblyai_api_key:
        raise RuntimeError(
            "AssemblyAI API key missing. Set the ASSEMBLYAI_API_KEY environment variable."
        )

    if aai is None:  # pragma: no cover - depends on optional dependency
        raise RuntimeError("assemblyai package is not installed") from _ASSEMBLYAI_IMPORT_ERROR

    path = Path(audio_path)
    if not path.exists():
        raise FileNotFoundError(path)

    aai.settings.api_key = config.assemblyai_api_key
    transcription_config = aai.TranscriptionConfig(speaker_labels=True)
    transcriber = aai.Transcriber()
    transcript = transcriber.transcribe(str(path), config=transcription_config)

    if transcript.status != "completed":
        error_detail = getattr(transcript, "error", "Unknown error")
        raise RuntimeError(f"Transcription failed: {error_detail}")

    labels = speaker_labels or {}
    utterances = [
        Utterance(
            speaker=apply_speaker_labels(utterance.speaker, labels),
            text=utterance.text,
            start=utterance.start,
            end=utterance.end,
        )
        for utterance in transcript.utterances or []
    ]

    return TranscriptionResult(text=transcript.text or "", utterances=utterances)


__all__ = [
    "Utterance",
    "TranscriptionResult",
    "transcribe_audio",
    "parse_speaker_labels",
    "apply_speaker_labels",
    "format_timestamp",
]
