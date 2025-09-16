import os
import wave
from pathlib import Path

from meeting_recorder.state import MeetingState


def _create_wav(path: Path, duration_frames: int = 16000) -> None:
    with wave.open(str(path), "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(16000)
        wav_file.writeframes(b"\x00\x00" * duration_frames)


def test_meeting_state_combines_segments(tmp_path):
    first = tmp_path / "segment1.wav"
    second = tmp_path / "segment2.wav"
    _create_wav(first)
    _create_wav(second)

    state = MeetingState()
    state.update_pending(str(first))
    state.pause()  # move pending to segments
    state.pause(str(second))

    final_path = state.stop()
    assert final_path is not None
    assert os.path.exists(final_path)
    assert state.final_recording == final_path


def test_meeting_state_reset_clears_data(tmp_path):
    segment = tmp_path / "segment.wav"
    _create_wav(segment)

    state = MeetingState()
    state.start()
    state.pause(str(segment))
    state.stop()
    state.update_label("A", "Alice")
    state.transcript = object()  # type: ignore[assignment]

    state.reset()

    assert state.segments == []
    assert state.pending_segment is None
    assert state.final_recording is None
    assert state.transcript is None
    assert state.speaker_labels == {}
