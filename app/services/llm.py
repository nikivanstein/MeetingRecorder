"""LLM integration helpers."""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import List, Optional

from openai import OpenAI


@dataclass
class SummaryResult:
    """Normalized output from the language model."""

    summary: str
    action_items: List[str]
    raw_response: str


class LLMServiceError(RuntimeError):
    """Raised when the LLM service is not available or fails."""


class OpenAILlmService:
    """Simple wrapper around OpenAI's chat completion API."""

    def __init__(self, api_key: Optional[str], model: str = "gpt-4o-mini") -> None:
        self.api_key = api_key
        self.model = model
        self._client = OpenAI(api_key=api_key) if api_key else None

    def summarize(self, transcript_text: str) -> SummaryResult:
        """Request a structured summary and list of action items from OpenAI."""

        if not transcript_text.strip():
            raise LLMServiceError("Transcript is empty; cannot summarize an empty meeting.")
        if not self._client:
            raise LLMServiceError("OpenAI API key is not configured. Set OPENAI_API_KEY.")

        system_message = (
            "You are an assistant that summarises business meetings. "
            "Return concise summaries and actionable bullet points."
        )
        user_prompt = (
            "Summarise the following meeting transcript and list clear action items. "
            "Respond with JSON using the keys 'summary' and 'action_items'. "
            "The 'action_items' value must be an array of strings.\n\n" + transcript_text
        )

        response = self._client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.2,
        )
        message = response.choices[0].message.content or ""

        summary, action_items = self._parse_response(message)
        return SummaryResult(summary=summary, action_items=action_items, raw_response=message)

    @staticmethod
    def _parse_response(message: str) -> tuple[str, List[str]]:
        """Parse JSON response, falling back to plain text if parsing fails."""

        try:
            payload = json.loads(message)
        except json.JSONDecodeError:
            return message.strip(), []

        summary = str(payload.get("summary", "")).strip()
        raw_action_items = payload.get("action_items", [])
        if isinstance(raw_action_items, list):
            action_items = [str(item).strip() for item in raw_action_items if str(item).strip()]
        elif isinstance(raw_action_items, str):
            action_items = [line.strip() for line in raw_action_items.splitlines() if line.strip()]
        else:
            action_items = []

        return summary, action_items


__all__ = ["OpenAILlmService", "SummaryResult", "LLMServiceError"]
