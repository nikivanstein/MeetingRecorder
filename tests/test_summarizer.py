import json
from typing import Any, Dict

import pytest

from meeting_recorder.summarizer import LLMSummarizer, SummarizationError


def test_summarizer_openai(monkeypatch):
    def fake_post(url: str, payload, headers=None, timeout=None):
        return {
            "choices": [
                {"message": {"content": json.dumps({"summary": "Sum", "action_items": "Act"})}}
            ]
        }

    monkeypatch.setattr("meeting_recorder.summarizer.post_json", fake_post)
    summarizer = LLMSummarizer(openai_api_key="test-key")
    result = summarizer.summarize("transcript text")
    assert result["summary"] == "Sum"
    assert result["action_items"] == "Act"


def test_summarizer_ollama(monkeypatch):
    def fake_post(url: str, payload, headers=None, timeout=None):
        return {"response": json.dumps({"summary": "S", "action_items": "A"})}

    monkeypatch.setattr("meeting_recorder.summarizer.post_json", fake_post)
    summarizer = LLMSummarizer(openai_api_key=None, ollama_endpoint="http://localhost:11434")
    result = summarizer.summarize("text")
    assert result == {"summary": "S", "action_items": "A"}


def test_summarizer_invalid_json(monkeypatch):
    def fake_post(url: str, payload, headers=None, timeout=None):
        return {"choices": [{"message": {"content": "not-json"}}]}

    monkeypatch.setattr("meeting_recorder.summarizer.post_json", fake_post)
    summarizer = LLMSummarizer(openai_api_key="test-key")
    with pytest.raises(SummarizationError):
        summarizer.summarize("text")
