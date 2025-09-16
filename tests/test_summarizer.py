"""Tests for the LLM summariser helpers."""

import json

import pytest

from meeting_recorder.summarizer import MeetingSummary, build_summary_prompt, parse_summary_response


def test_build_summary_prompt_includes_transcript() -> None:
    transcript = "Alice: Hello"
    prompt = build_summary_prompt(transcript)
    assert "Alice: Hello" in prompt
    assert "Respond in JSON" in prompt


def test_parse_summary_response_from_valid_json() -> None:
    payload = {"summary": "Important decisions", "action_items": ["Follow up"]}
    summary = parse_summary_response(json.dumps(payload))
    assert summary == MeetingSummary(summary="Important decisions", action_items=["Follow up"])


def test_parse_summary_response_with_string_action_items() -> None:
    payload = {"summary": "Discussed roadmap", "action_items": "- Task one\n- Task two"}
    summary = parse_summary_response(json.dumps(payload))
    assert summary.action_items == ["Task one", "Task two"]


def test_parse_summary_response_invalid_json() -> None:
    with pytest.raises(ValueError):
        parse_summary_response("not-json")
