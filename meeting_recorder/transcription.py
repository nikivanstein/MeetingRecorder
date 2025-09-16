"""Transcription services for the Meeting Recorder app."""

from __future__ import annotations

import time
from typing import Dict, Optional

from .http import get_json, post_bytes, post_json
from .models import TranscriptResult, TranscriptSegment


class TranscriptionError(RuntimeError):
    """Raised when the external transcription service fails."""


class AssemblyAITranscriber:
    """Thin wrapper around the AssemblyAI API with diarization enabled."""

    def __init__(self, api_key: str, poll_interval: float = 3.0) -> None:
        if not api_key:
            raise ValueError("An AssemblyAI API key is required")
        self.api_key = api_key
        self.poll_interval = poll_interval
        self.base_url = "https://api.assemblyai.com/v2"
        self._headers = {"authorization": self.api_key}

    def transcribe(self, audio_path: str, speaker_labels: Optional[Dict[str, str]] = None) -> TranscriptResult:
        """Transcribe an audio file and enrich the response with speaker labels."""

        upload_url = self._upload_file(audio_path)
        transcript_id = self._start_transcription(upload_url)
        response = self._poll_transcription(transcript_id)
        return self._parse_transcript(response, speaker_labels)

    def _upload_file(self, audio_path: str) -> str:
        with open(audio_path, "rb") as audio_file:
            response = post_bytes(
                f"{self.base_url}/upload",
                data=audio_file.read(),
                headers=self._headers,
                timeout=60,
            )
        return response["upload_url"]

    def _start_transcription(self, upload_url: str) -> str:
        payload = {
            "audio_url": upload_url,
            "speaker_labels": True,
            "auto_chapters": False,
        }
        try:
            response = post_json(
                f"{self.base_url}/transcript",
                payload,
                headers=self._headers,
                timeout=30,
            )
        except Exception as exc:  # pragma: no cover - network failure
            raise TranscriptionError(f"Failed to start transcription: {exc}") from exc
        return response["id"]

    def _poll_transcription(self, transcript_id: str) -> Dict:
        status_url = f"{self.base_url}/transcript/{transcript_id}"
        while True:
            try:
                data = get_json(status_url, headers=self._headers, timeout=30)
            except Exception as exc:  # pragma: no cover - network failure
                raise TranscriptionError(f"Polling failed: {exc}") from exc
            status = data.get("status")
            if status == "completed":
                return data
            if status == "error":
                raise TranscriptionError(data.get("error", "Unknown error during transcription"))
            time.sleep(self.poll_interval)

    @staticmethod
    def _parse_transcript(
        payload: Dict,
        speaker_labels: Optional[Dict[str, str]] = None,
    ) -> TranscriptResult:
        text = payload.get("text", "")
        speaker_map = speaker_labels or {}
        segments = []
        for entry in payload.get("utterances", []) or []:
            speaker = speaker_map.get(entry.get("speaker"), entry.get("speaker", "Speaker"))
            segments.append(
                TranscriptSegment(
                    speaker=speaker,
                    text=entry.get("text", ""),
                    start=_safe_float(entry.get("start")),
                    end=_safe_float(entry.get("end")),
                )
            )
        return TranscriptResult(text=text, segments=segments)


def _safe_float(value: Optional[float]) -> Optional[float]:
    try:
        if value is None:
            return None
        return float(value) / 1000 if value > 1000 else float(value)
    except (TypeError, ValueError):
        return None
