"""Utilities for summarising meeting transcripts with an LLM."""

from __future__ import annotations

import json
from typing import Dict, Optional

from .http import HTTPError, post_json


class SummarizationError(RuntimeError):
    """Raised when the LLM fails to return a valid response."""


class LLMSummarizer:
    """Generate summaries and action items from a transcript."""

    def __init__(
        self,
        openai_api_key: Optional[str] = None,
        ollama_endpoint: Optional[str] = None,
        openai_model: str = "gpt-4o-mini",
        ollama_model: str = "llama3",
    ) -> None:
        if not openai_api_key and not ollama_endpoint:
            raise ValueError("Either an OpenAI API key or an Ollama endpoint must be provided")
        self.openai_api_key = openai_api_key
        self.ollama_endpoint = ollama_endpoint.rstrip("/") if ollama_endpoint else None
        self.openai_model = openai_model
        self.ollama_model = ollama_model

    def summarize(self, transcript_text: str) -> Dict[str, str]:
        """Summarise the transcript and extract action items."""

        prompt = (
            "You are an assistant that analyses meeting transcripts. "
            "Return a JSON object with two keys: 'summary' containing a concise "
            "paragraph and 'action_items' containing bullet points of follow-up "
            "tasks. Only return valid JSON. Transcript:\n" + transcript_text
        )
        if self.openai_api_key:
            return self._summarize_openai(prompt)
        return self._summarize_ollama(prompt)

    def _summarize_openai(self, prompt: str) -> Dict[str, str]:
        headers = {"Authorization": f"Bearer {self.openai_api_key}"}
        payload = {
            "model": self.openai_model,
            "messages": [
                {"role": "system", "content": "You are a helpful meeting assistant."},
                {"role": "user", "content": prompt},
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.2,
        }
        try:
            response = post_json(
                "https://api.openai.com/v1/chat/completions",
                payload,
                headers=headers,
                timeout=60,
            )
        except HTTPError as exc:  # pragma: no cover - network failure
            raise SummarizationError(f"OpenAI request failed: {exc.body}") from exc
        content = response["choices"][0]["message"]["content"]
        return _load_json(content)

    def _summarize_ollama(self, prompt: str) -> Dict[str, str]:
        if not self.ollama_endpoint:
            raise SummarizationError("An Ollama endpoint is required for Ollama summarisation")
        payload = {
            "model": self.ollama_model,
            "prompt": prompt,
            "stream": False,
        }
        try:
            response = post_json(
                f"{self.ollama_endpoint}/api/generate",
                payload,
                timeout=60,
            )
        except HTTPError as exc:  # pragma: no cover - network failure
            raise SummarizationError(f"Ollama request failed: {exc.body}") from exc
        content = response.get("response", "{}").strip()
        return _load_json(content)


def _load_json(content: str) -> Dict[str, str]:
    try:
        data = json.loads(content)
        if not isinstance(data, dict):
            raise ValueError
        return {
            "summary": data.get("summary", ""),
            "action_items": data.get("action_items", ""),
        }
    except (ValueError, json.JSONDecodeError) as exc:  # pragma: no cover - defensive
        raise SummarizationError("Invalid JSON received from LLM") from exc
