"""Unit tests for transcription helper utilities."""

from meeting_recorder.transcription import (
    apply_speaker_labels,
    format_timestamp,
    parse_speaker_labels,
)


def test_parse_speaker_labels_supports_multiple_separators() -> None:
    labels = parse_speaker_labels("Speaker A=Alice,Speaker B=Bob;C:Charlie")
    assert labels == {"speaker a": "Alice", "speaker b": "Bob", "c": "Charlie"}


def test_apply_speaker_labels_defaults_when_unknown() -> None:
    mapping = {"speaker a": "Alice"}
    assert apply_speaker_labels("Speaker A", mapping) == "Alice"
    assert apply_speaker_labels("B", mapping) == "Speaker B"
    assert apply_speaker_labels(None, mapping) == "Speaker"


def test_format_timestamp() -> None:
    assert format_timestamp(0) == "00:00:00"
    assert format_timestamp(65_000) == "00:01:05"
    assert format_timestamp(3_600_000) == "01:00:00"
