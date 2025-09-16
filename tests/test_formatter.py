"""Unit tests for formatter helpers."""
from __future__ import annotations

from app.services.formatter import (
    apply_speaker_overrides,
    build_result_document,
    format_transcript_text,
)
from app.services.transcription import TranscriptionSegment


def make_segment(speaker: str, text: str, start: float) -> TranscriptionSegment:
    return TranscriptionSegment(speaker=speaker, text=text, start=start, end=start + 1)


def test_format_transcript_text_with_overrides() -> None:
    segments = [
        make_segment("Speaker 1", "Hello there", 0),
        make_segment("Speaker 2", "General Kenobi", 5),
    ]

    text = format_transcript_text(segments, overrides={"Speaker 2": "Obi-Wan"})

    assert "Speaker 1" in text
    assert "Obi-Wan" in text
    assert "General Kenobi" in text


def test_apply_speaker_overrides_preserves_order() -> None:
    segments = [make_segment("Speaker 1", "Test", 0), make_segment("Speaker 1", "Again", 1)]
    rendered = apply_speaker_overrides(segments, overrides={"Speaker 1": "Alice"})
    assert [segment.text for segment in rendered] == ["Test", "Again"]
    assert all(segment.speaker == "Alice" for segment in rendered)


def test_build_result_document_contains_all_sections() -> None:
    segments = [make_segment("Speaker 1", "First", 0)]
    document = build_result_document("Summary", ["Item"], segments)

    assert "Meeting Summary" in document
    assert "Action Items" in document
    assert "Transcript" in document
    assert "Item" in document
    assert "First" in document
