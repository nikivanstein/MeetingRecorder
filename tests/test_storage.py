from pathlib import Path

from meeting_recorder.models import SpeakerSegment, TranscriptionResult
from meeting_recorder.storage import save_meeting_artifacts, serialise_segments


def build_transcription() -> TranscriptionResult:
    segments = [
        SpeakerSegment(speaker="Speaker 1", start=0.0, end=5.0, text="Intro"),
        SpeakerSegment(speaker="Speaker 2", start=5.0, end=10.0, text="Action item"),
    ]
    return TranscriptionResult(segments=segments)


def test_serialise_segments_formats_text():
    result = serialise_segments(build_transcription().segments)
    assert "Speaker 1" in result
    assert "00:05" in result


def test_save_meeting_artifacts_writes_file(tmp_path: Path):
    transcription = build_transcription()
    summary = {"summary": "Summary text", "action_items": [{"description": "Action", "owner": "Dana"}]}
    artifacts = save_meeting_artifacts(transcription, summary, output_dir=tmp_path)
    assert artifacts.summary_path.exists()
    assert artifacts.transcript_path.exists()
    contents = artifacts.summary_path.read_text()
    assert "Summary text" in contents
    assert "Dana" in contents
    transcript_contents = artifacts.transcript_path.read_text()
    assert "Speaker 1" in transcript_contents
