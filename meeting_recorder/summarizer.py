"""Utilities for summarising meetings and extracting action items."""

from __future__ import annotations

import json
import os
from abc import ABC, abstractmethod
from typing import Dict, List, Sequence

try:
    import requests
except ModuleNotFoundError:  # pragma: no cover - optional dependency
    requests = None  # type: ignore

try:
    from openai import OpenAI
except ModuleNotFoundError:  # pragma: no cover - optional dependency
    OpenAI = None  # type: ignore

from .models import SpeakerSegment, TranscriptionResult


class Summariser(ABC):
    """Base interface for large language model summaries."""

    @abstractmethod
    def summarise(self, transcript: TranscriptionResult) -> Dict[str, object]:
        """Return a structured summary with ``summary`` and ``action_items`` keys."""


class OpenAISummariser(Summariser):
    """Summariser backed by the OpenAI chat completion API."""

    def __init__(self, api_key: str, model: str | None = None, base_url: str | None = None) -> None:
        if not api_key:
            raise ValueError("OpenAI API key is required")
        if OpenAI is None:
            raise RuntimeError("The openai package is required for the OpenAI summariser.")
        self.api_key = api_key
        self.model = model or os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
        self.base_url = base_url or os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")
        client_kwargs = {"api_key": api_key}
        if self.base_url:
            client_kwargs["base_url"] = self.base_url
        self.client = OpenAI(**client_kwargs)
        self._client = self.client.with_options(timeout=60)


    def summarise(self, transcript: TranscriptionResult) -> Dict[str, object]:  # noqa: D401 - inherited
        completion = self._client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are an assistant that creates meeting minutes. "
                        "Reply in JSON with keys 'summary' (a multi-paragraph summary) and "
                        "'action_items' (a list of objects with 'description' and optional 'owner')."
                    ),
                },
                {
                    "role": "user",
                    "content": _segments_to_prompt(transcript.segments),
                },
            ],
            temperature=0.2,
            response_format={"type": "json_object"},
        )
        choice = completion.choices[0]
        content = choice.message.content or "{}"
        return _parse_summary_response(content)


class OllamaSummariser(Summariser):
    """Summariser backed by an Ollama instance."""

    def __init__(self, base_url: str | None = None, model: str | None = None) -> None:
        self.base_url = base_url or os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
        self.model = model or os.environ.get("OLLAMA_MODEL", "llama3")

        if requests is None:
            raise RuntimeError("The requests package is required for the Ollama summariser.")

    def summarise(self, transcript: TranscriptionResult) -> Dict[str, object]:  # noqa: D401 - inherited
        prompt = (
            "You produce meeting summaries. Return JSON with 'summary' and 'action_items'.\n"
            + _segments_to_prompt(transcript.segments)
        )
        response = requests.post(
            f"{self.base_url.rstrip('/')}/api/generate",
            json={"model": self.model, "prompt": prompt, "format": "json"},
            timeout=120,
        )
        response.raise_for_status()
        data = response.json()
        content = data.get("response", "{}")
        return _parse_summary_response(content)


class DummySummariser(Summariser):
    """A predictable summariser used for tests and offline usage."""

    def summarise(self, transcript: TranscriptionResult) -> Dict[str, object]:  # noqa: D401 - inherited
        summary = f"Meeting recap involving {len(transcript.segments)} segments."
        actions: List[Dict[str, str]] = []
        for segment in transcript.segments:
            if "action" in segment.text.lower():
                actions.append({"description": segment.text, "owner": segment.speaker})
        return {"summary": summary, "action_items": actions}


def get_summariser() -> Summariser:
    """Return the best available summariser based on environment variables."""

    if os.environ.get("OPENAI_API_KEY"):
        return OpenAISummariser(api_key=os.environ["OPENAI_API_KEY"])
    if os.environ.get("OLLAMA_BASE_URL"):
        return OllamaSummariser()
    return DummySummariser()


def _segments_to_prompt(segments: Sequence[SpeakerSegment]) -> str:
    lines = [
        "Summarise the following meeting transcript. Each line contains start/end timestamps and the speaker name:",
    ]
    for segment in segments:
        lines.append(
            f"- [{_format_timestamp(segment.start)} - {_format_timestamp(segment.end)}] {segment.speaker}: {segment.text}"
        )
    return "\n".join(lines)


def _parse_summary_response(content: str) -> Dict[str, object]:
    try:
        parsed = json.loads(content)
    except json.JSONDecodeError as exc:  # pragma: no cover - defensive branch
        raise ValueError("Failed to parse summary response") from exc
    summary = parsed.get("summary") or "Summary unavailable."
    action_items = parsed.get("action_items") or []
    if isinstance(action_items, list):
        normalised: List[Dict[str, str]] = []
        for item in action_items:
            if isinstance(item, dict):
                normalised.append(
                    {
                        "description": str(item.get("description") or item.get("task") or ""),
                        "owner": str(item.get("owner") or item.get("assignee") or "Unassigned"),
                    }
                )
            else:
                normalised.append({"description": str(item), "owner": "Unassigned"})
        action_items = [item for item in normalised if item["description"]]
    else:
        action_items = []
    return {"summary": str(summary), "action_items": action_items}


def _format_timestamp(value: float) -> str:
    minutes, seconds = divmod(int(value), 60)
    return f"{minutes:02d}:{seconds:02d}"


__all__ = [
    "DummySummariser",
    "OllamaSummariser",
    "OpenAISummariser",
    "Summariser",
    "get_summariser",
]
