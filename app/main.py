"""Flask application providing the meeting recorder API."""
from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List

from flask import Flask, jsonify, render_template, request

from .config import settings
from .services.emailer import EmailNotConfiguredError, EmailSender
from .services.formatter import build_result_document, format_transcript_text
from .services.llm import LLMServiceError, OpenAILlmService
from .services.transcription import (
    AssemblyAITranscriptionService,
    TranscriptionSegment,
    TranscriptionServiceError,
)

LOGGER = logging.getLogger(__name__)


def _base_path() -> Path:
    return Path(__file__).resolve().parent.parent


def _create_directories() -> None:
    base = _base_path()
    for folder in (base / "data" / "recordings", base / "data" / "results"):
        folder.mkdir(parents=True, exist_ok=True)


def create_app() -> Flask:
    """Create and configure the Flask application."""

    _create_directories()
    base = _base_path()

    app = Flask(
        __name__,
        static_folder=str(base / "static"),
        template_folder=str(base / "templates"),
    )

    transcriber = AssemblyAITranscriptionService(settings.assemblyai_api_key)
    llm = OpenAILlmService(settings.openai_api_key, settings.openai_model)
    email_sender = EmailSender(settings.email)

    upload_dir = base / "data" / "recordings"
    result_dir = base / "data" / "results"

    @app.route("/")
    def index() -> str:
        return render_template(
            "index.html",
            email_enabled=settings.email.enabled,
            default_recipient=settings.email.default_recipient or "",
        )

    @app.post("/upload")
    def upload_audio():  # type: ignore[override]
        if "audio" not in request.files:
            return jsonify({"error": "No audio file supplied."}), 400

        audio_file = request.files["audio"]
        if not audio_file.filename:
            return jsonify({"error": "Uploaded file has no filename."}), 400

        extension = Path(audio_file.filename).suffix or ".webm"
        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        output_name = f"meeting_{timestamp}{extension}"
        destination = upload_dir / output_name
        audio_file.save(destination)
        LOGGER.info("Saved recording to %s", destination)

        try:
            transcription = transcriber.transcribe(destination)
            transcript_text = format_transcript_text(transcription.segments)
            llm_result = llm.summarize(transcript_text or transcription.text)
        except TranscriptionServiceError as exc:
            LOGGER.exception("Transcription failed")
            return jsonify({"error": str(exc)}), 500
        except LLMServiceError as exc:
            LOGGER.exception("LLM summarisation failed")
            return jsonify({"error": str(exc)}), 500
        except Exception:  # pragma: no cover - defensive logging
            LOGGER.exception("Unexpected error during processing")
            return jsonify({"error": "Unexpected error processing the recording."}), 500

        return jsonify(
            {
                "fileName": output_name,
                "segments": [
                    {
                        "speaker": segment.speaker,
                        "text": segment.text,
                        "start": segment.start,
                        "end": segment.end,
                    }
                    for segment in transcription.segments
                ],
                "summary": llm_result.summary,
                "actionItems": llm_result.action_items,
                "transcriptText": transcript_text,
            }
        )

    def _decode_segments(payload: Iterable[Dict]) -> List[TranscriptionSegment]:
        segments: List[TranscriptionSegment] = []
        for item in payload:
            segments.append(
                TranscriptionSegment(
                    speaker=str(item.get("speaker", "Speaker")),
                    text=str(item.get("text", "")),
                    start=float(item.get("start", 0.0)),
                    end=float(item.get("end", 0.0)),
                )
            )
        return segments

    @app.post("/save_result")
    def save_result():  # type: ignore[override]
        data = request.get_json(silent=True) or {}
        summary = str(data.get("summary", ""))
        action_items = data.get("actionItems") or []
        if not isinstance(action_items, list):
            action_items = []
        segments_payload = data.get("segments") or []
        overrides = data.get("speakerMap") or {}
        file_name = data.get("fileName") or f"meeting_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}.txt"

        segments = _decode_segments(segments_payload)
        document = build_result_document(summary, action_items, segments, overrides)
        destination = result_dir / file_name
        destination.write_text(document, encoding="utf-8")

        email_status = None
        if data.get("sendEmail"):
            recipient = data.get("emailAddress") or None
            try:
                email_sender.send("Meeting Summary", document, recipient=recipient)
                email_status = "sent"
            except EmailNotConfiguredError as exc:
                return jsonify({"error": str(exc)}), 400
            except Exception:  # pragma: no cover - defensive logging
                LOGGER.exception("Email dispatch failed")
                return jsonify({"error": "Failed to send email."}), 500

        return jsonify({"savedTo": str(destination), "emailStatus": email_status})

    return app


app = create_app()

__all__ = ["app", "create_app"]
