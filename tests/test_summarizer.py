from meeting_recorder.models import SpeakerSegment, TranscriptionResult
from meeting_recorder.summarizer import DummySummariser, _parse_summary_response


def build_transcript() -> TranscriptionResult:
    segments = [
        SpeakerSegment(speaker="A", start=0, end=5, text="Introduction"),
        SpeakerSegment(speaker="B", start=5, end=10, text="Action: send report"),
    ]
    return TranscriptionResult(segments=segments)


def test_dummy_summariser_extracts_actions():
    summary = DummySummariser().summarise(build_transcript())
    assert summary["action_items"][0]["owner"] == "B"


def test_parse_summary_response_handles_strings():
    payload = '{"summary": "Done", "action_items": ["Task one"]}'
    parsed = _parse_summary_response(payload)
    assert parsed["action_items"][0]["description"] == "Task one"
