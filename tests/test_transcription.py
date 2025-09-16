from meeting_recorder.transcription import AssemblyAITranscriber


def test_parse_transcript_applies_labels():
    payload = {
        "text": "Hello",
        "utterances": [
            {"speaker": "A", "text": "Hi there", "start": 0, "end": 1500},
            {"speaker": "B", "text": "Hello", "start": 1500, "end": 3000},
        ],
    }
    result = AssemblyAITranscriber._parse_transcript(payload, {"A": "Alice"})
    assert result.text == "Hello"
    assert result.segments[0].speaker == "Alice"
    assert result.segments[0].start == 0
    assert result.segments[0].end == 1.5
    assert result.segments[1].speaker == "B"
