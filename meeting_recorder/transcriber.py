"""Transcription utilities with diarisation support."""

from __future__ import annotations

import os
import time
from abc import ABC, abstractmethod
from typing import BinaryIO, Iterable, List

try:
    import requests
except ModuleNotFoundError:  # pragma: no cover - optional dependency
    requests = None  # type: ignore

from .models import SpeakerSegment, TranscriptionResult


class Transcriber(ABC):
    """Base interface for converting audio files into transcripts."""

    @abstractmethod
    def transcribe(self, audio_path: str) -> TranscriptionResult:
        """Transcribe the provided audio file and return diarised segments."""


class AssemblyAITranscriber(Transcriber):
    """Transcriber backed by the AssemblyAI API.

    The implementation performs a file upload, triggers a transcription job with
    speaker diarisation enabled, and then polls for completion.
    """

    def __init__(self, api_key: str, poll_interval: float = 3.0) -> None:
        if not api_key:
            raise ValueError("AssemblyAI API key is required")
        if requests is None:
            raise RuntimeError("The requests package is required for AssemblyAI integration.")
        self.api_key = api_key
        self.poll_interval = poll_interval
        self._base_url = "https://api.assemblyai.com/v2"

    @property
    def headers(self) -> dict:
        return {"authorization": self.api_key, "content-type": "application/json"}

    def _upload(self, audio_path: str) -> str:
        with open(audio_path, "rb") as stream:
            response = requests.post(
                f"{self._base_url}/upload",
                headers={"authorization": self.api_key},
                data=_read_in_chunks(stream),
                timeout=60,
            )
        response.raise_for_status()
        return response.json()["upload_url"]

    def _request_transcription(self, upload_url: str) -> str:
        response = requests.post(
            f"{self._base_url}/transcript",
            headers=self.headers,
            json={"audio_url": upload_url, "speaker_labels": True},
            timeout=30,
        )
        response.raise_for_status()
        return response.json()["id"]

    def _poll(self, transcript_id: str) -> dict:
        url = f"{self._base_url}/transcript/{transcript_id}"
        while True:
            response = requests.get(url, headers=self.headers, timeout=30)
            response.raise_for_status()
            payload = response.json()
            status = payload.get("status")
            if status == "completed":
                return payload
            if status == "error":
                raise RuntimeError(f"AssemblyAI transcription failed: {payload}")
            time.sleep(self.poll_interval)

    def _segments_from_payload(self, payload: dict) -> List[SpeakerSegment]:
        segments: List[SpeakerSegment] = []
        utterances = payload.get("utterances") or []
        for item in utterances:
            speaker = item.get("speaker", "Speaker")
            start = float(item.get("start", 0.0)) / 1000.0
            end = float(item.get("end", 0.0)) / 1000.0
            text = item.get("text", "").strip()
            if text:
                segments.append(SpeakerSegment(speaker=speaker, start=start, end=end, text=text))
        if not segments:
            text_chunks = payload.get("text", "").split(". ")
            segments = [
                SpeakerSegment(speaker="Speaker 1", start=0.0, end=0.0, text=chunk.strip())
                for chunk in text_chunks
                if chunk
            ]
        return segments

    def transcribe(self, audio_path: str) -> TranscriptionResult:
        upload_url = self._upload(audio_path)
        transcript_id = self._request_transcription(upload_url)
        payload = self._poll(transcript_id)
        segments = self._segments_from_payload(payload)
        return TranscriptionResult(segments=segments)


class DummyTranscriber(Transcriber):
    """A deterministic fallback used when no external service is configured."""

    def transcribe(self, audio_path: str) -> TranscriptionResult:  # noqa: D401 - inherited docstring
        base_name = os.path.basename(audio_path) or "recording"
        segments = [
            SpeakerSegment(speaker="Speaker 1", start=0.0, end=10.0, text=f"Introductory remarks from {base_name}.")
        ]
        segments.append(
            SpeakerSegment(
                speaker="Speaker 2",
                start=10.0,
                end=20.0,
                text="Action items were discussed, including preparing follow-up notes.",
            )
        )
        return TranscriptionResult(segments=segments)


def get_transcriber() -> Transcriber:
    """Return the most appropriate transcriber based on environment variables."""

    api_key = os.environ.get("ASSEMBLYAI_API_KEY") or os.environ.get("ASSEMBLY_AI_KEY")
    if api_key:
        return AssemblyAITranscriber(api_key=api_key)
    return DummyTranscriber()


def _read_in_chunks(stream: BinaryIO, chunk_size: int = 5_242_880) -> Iterable[bytes]:
    """Yield audio bytes in chunks suited for the AssemblyAI upload endpoint."""

    while True:
        chunk = stream.read(chunk_size)
        if not chunk:
            break
        yield chunk


__all__ = [
    "AssemblyAITranscriber",
    "DummyTranscriber",
    "Transcriber",
    "get_transcriber",
]
