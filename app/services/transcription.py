"""Utilities for transcribing recorded meetings."""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional

try:  # pragma: no cover - dependency may be missing during tests
    import requests
except ModuleNotFoundError:  # pragma: no cover
    requests = None  # type: ignore[assignment]

LOGGER = logging.getLogger(__name__)


@dataclass
class TranscriptionSegment:
    """Represents a single speaker segment in a transcription."""

    speaker: str
    text: str
    start: float
    end: float


@dataclass
class TranscriptionResult:
    """Aggregate result of a transcription request."""

    text: str
    segments: List[TranscriptionSegment]
    duration_seconds: Optional[float] = None


class TranscriptionServiceError(RuntimeError):
    """Raised when the transcription service fails to process the audio."""


class AssemblyAITranscriptionService:
    """Wrapper around AssemblyAI's transcription API."""

    _UPLOAD_ENDPOINT = "https://api.assemblyai.com/v2/upload"
    _TRANSCRIPT_ENDPOINT = "https://api.assemblyai.com/v2/transcript"

    def __init__(self, api_key: Optional[str]) -> None:
        self.api_key = api_key

    def _headers(self) -> dict[str, str]:
        if not self.api_key:
            raise TranscriptionServiceError(
                "AssemblyAI API key is not configured. Set ASSEMBLYAI_API_KEY."
            )
        return {"authorization": self.api_key}

    @staticmethod
    def _read_file(path: Path, chunk_size: int = 5_242_880) -> Iterable[bytes]:
        """Yield chunks from the given file path suitable for streaming uploads."""

        with path.open("rb") as handle:
            while True:
                data = handle.read(chunk_size)
                if not data:
                    break
                yield data

    def _upload_audio(self, audio_path: Path) -> str:
        if requests is None:
            raise TranscriptionServiceError("The 'requests' package is required for transcription.")
        headers = self._headers()
        LOGGER.debug("Uploading %s to AssemblyAI", audio_path)
        response = requests.post(
            self._UPLOAD_ENDPOINT,
            headers=headers,
            data=self._read_file(audio_path),
        )
        response.raise_for_status()
        upload_url = response.json()["upload_url"]
        LOGGER.debug("Upload successful: %s", upload_url)
        return upload_url

    def _request_transcription(self, upload_url: str) -> str:
        if requests is None:
            raise TranscriptionServiceError("The 'requests' package is required for transcription.")
        headers = self._headers()
        LOGGER.debug("Requesting transcription for %s", upload_url)
        response = requests.post(
            self._TRANSCRIPT_ENDPOINT,
            headers=headers,
            json={
                "audio_url": upload_url,
                "speaker_labels": True,
                "auto_highlights": False,
            },
        )
        response.raise_for_status()
        transcript_id = response.json()["id"]
        LOGGER.debug("Transcript job created: %s", transcript_id)
        return transcript_id

    def _poll_transcription(self, transcript_id: str, interval: float = 3.0) -> dict:
        if requests is None:
            raise TranscriptionServiceError("The 'requests' package is required for transcription.")
        headers = self._headers()
        status_endpoint = f"{self._TRANSCRIPT_ENDPOINT}/{transcript_id}"
        while True:
            response = requests.get(status_endpoint, headers=headers)
            response.raise_for_status()
            payload = response.json()
            status = payload.get("status")
            LOGGER.debug("Transcript %s status: %s", transcript_id, status)
            if status == "completed":
                return payload
            if status == "error":
                raise TranscriptionServiceError(payload.get("error", "Unknown error"))
            time.sleep(interval)

    def transcribe(self, audio_path: Path) -> TranscriptionResult:
        """Transcribe the audio file, returning diarised segments."""

        upload_url = self._upload_audio(audio_path)
        transcript_id = self._request_transcription(upload_url)
        payload = self._poll_transcription(transcript_id)

        utterances = payload.get("utterances") or []
        segments: List[TranscriptionSegment] = []
        speaker_labels: dict[str, str] = {}

        for utterance in utterances:
            raw_label = utterance.get("speaker", "Unknown")
            if raw_label not in speaker_labels:
                speaker_labels[raw_label] = f"Speaker {len(speaker_labels) + 1}"
            label = speaker_labels[raw_label]
            segments.append(
                TranscriptionSegment(
                    speaker=label,
                    text=utterance.get("text", "").strip(),
                    start=float(utterance.get("start", 0)) / 1000.0,
                    end=float(utterance.get("end", 0)) / 1000.0,
                )
            )

        combined_text = " ".join(segment.text for segment in segments).strip()
        duration = payload.get("audio_duration")
        return TranscriptionResult(
            text=combined_text,
            segments=segments,
            duration_seconds=float(duration) if duration is not None else None,
        )


__all__ = [
    "AssemblyAITranscriptionService",
    "TranscriptionResult",
    "TranscriptionSegment",
    "TranscriptionServiceError",
]
