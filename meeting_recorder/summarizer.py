"""Summarisation utilities for meeting transcripts."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

try:  # pragma: no cover - optional dependency when running tests
    import requests
except Exception as exc:  # pragma: no cover - handled during runtime
    requests = None  # type: ignore
    _REQUESTS_IMPORT_ERROR = exc
else:  # pragma: no cover - executed when dependency installed
    _REQUESTS_IMPORT_ERROR = None

try:  # pragma: no cover - optional dependency during testing
    from openai import OpenAI
except Exception:  # pragma: no cover - fallback when OpenAI SDK is absent
    OpenAI = None  # type: ignore

from .config import AppConfig


@dataclass(slots=True)
class MeetingSummary:
    """Structured summary extracted from a meeting transcript."""

    summary: str
    action_items: List[str]

    def format_markdown(self) -> str:
        """Represent the summary and action items in Markdown."""

        lines = ["## Summary", self.summary or "No summary generated."]
        lines.append("\n## Action Items")
        if self.action_items:
            for item in self.action_items:
                lines.append(f"- {item}")
        else:
            lines.append("- No action items identified.")
        return "\n".join(lines)


def build_summary_prompt(transcript: str) -> str:
    """Return the prompt instructing the LLM how to summarise the transcript."""

    return (
        "You are a helpful meeting assistant. "
        "Summarise the meeting transcript and extract clear action items. "
        "Respond in JSON with keys 'summary' (string) and 'action_items' (list of strings)."
        "\n\nTranscript:\n"
        f"{transcript.strip()}"
    )


def parse_summary_response(model_response: str) -> MeetingSummary:
    """Parse the JSON response returned by the LLM."""

    try:
        payload: Dict[str, object] = json.loads(model_response)
    except json.JSONDecodeError as exc:  # pragma: no cover - defensive parsing
        raise ValueError("Model response is not valid JSON") from exc

    summary = str(payload.get("summary", "")).strip()
    raw_items = payload.get("action_items", [])
    action_items: List[str] = []
    if isinstance(raw_items, list):
        action_items = [str(item).strip() for item in raw_items if str(item).strip()]
    elif isinstance(raw_items, str) and raw_items.strip():
        # Models occasionally return a single string containing bullet points.
        action_items = [segment.strip(" -") for segment in raw_items.splitlines() if segment.strip()]

    return MeetingSummary(summary=summary, action_items=action_items)


class LLMSummarizer:
    """Summarise transcripts using either OpenAI or a local Ollama model."""

    def __init__(
        self,
        config: AppConfig,
        openai_client: Optional[OpenAI] = None,
        http_session: Optional[Any] = None,
    ) -> None:
        self.config = config
        self._openai_client = openai_client
        if http_session is not None:
            self._http_session = http_session
        elif requests is not None:
            self._http_session = requests.Session()
        else:  # pragma: no cover - triggered only when requests is absent
            self._http_session = None

    def summarise(self, transcript: str) -> MeetingSummary:
        """Summarise a transcript and extract action items."""

        if not transcript.strip():
            raise ValueError("Transcript is empty; cannot summarise")

        if self.config.openai_api_key:
            return self._summarise_with_openai(transcript)
        if self.config.ollama_model:
            return self._summarise_with_ollama(transcript)
        raise RuntimeError(
            "No LLM configured. Set OPENAI_API_KEY or OLLAMA_MODEL in the environment."
        )

    # ------------------------------------------------------------------
    # Provider specific implementations
    # ------------------------------------------------------------------
    def _summarise_with_openai(self, transcript: str) -> MeetingSummary:
        if OpenAI is None:
            raise RuntimeError("openai package not available. Install the official SDK.")

        client = self._openai_client or OpenAI(api_key=self.config.openai_api_key)
        prompt = build_summary_prompt(transcript)
        response = client.chat.completions.create(  # type: ignore[attr-defined]
            model=self.config.openai_model,
            messages=[
                {"role": "system", "content": "You are a professional meeting assistant."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
        )
        message = response.choices[0].message.content  # type: ignore[index]
        if not message:
            raise RuntimeError("OpenAI response did not include any content")
        return parse_summary_response(message)

    def _summarise_with_ollama(self, transcript: str) -> MeetingSummary:
        if self._http_session is None:  # pragma: no cover - depends on optional dependency
            raise RuntimeError("requests package is not installed") from _REQUESTS_IMPORT_ERROR
        prompt = build_summary_prompt(transcript)
        payload = {"model": self.config.ollama_model, "prompt": prompt, "stream": False}
        response = self._http_session.post(
            "http://localhost:11434/api/generate", timeout=300, json=payload
        )
        response.raise_for_status()
        body = response.json()
        message = body.get("response", "")
        if not isinstance(message, str) or not message.strip():
            raise RuntimeError("Ollama did not return any content")
        return parse_summary_response(message)


__all__ = [
    "LLMSummarizer",
    "MeetingSummary",
    "build_summary_prompt",
    "parse_summary_response",
]
