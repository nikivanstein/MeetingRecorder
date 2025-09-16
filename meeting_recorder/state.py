"""State management utilities for the Meeting Recorder app."""

from __future__ import annotations

import os
import shutil
import tempfile
import wave
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class MeetingState:
    """Keep track of audio segments and recording metadata."""

    segments: List[str] = field(default_factory=list)
    pending_segment: Optional[str] = None
    is_recording: bool = False
    final_recording: Optional[str] = None
    speaker_labels: Dict[str, str] = field(default_factory=dict)
    transcript: Optional["TranscriptResult"] = None

    def start(self) -> None:
        """Mark the recording as in progress."""

        self.is_recording = True

    def queue_segment(self, segment_path: Optional[str]) -> None:
        """Store an audio segment if present."""

        if segment_path and os.path.exists(segment_path):
            self.segments.append(segment_path)
        self.pending_segment = None

    def pause(self, segment_path: Optional[str] = None) -> None:
        """Pause the recording and persist the current audio segment."""

        if segment_path:
            self.queue_segment(segment_path)
        elif self.pending_segment:
            self.queue_segment(self.pending_segment)
        self.is_recording = False

    def stop(self, segment_path: Optional[str] = None) -> Optional[str]:
        """Stop the recording, consolidating audio segments into one file."""

        self.pause(segment_path)
        if not self.segments:
            self.final_recording = None
            return None
        self.final_recording = self._combine_segments()
        self.segments.clear()
        return self.final_recording

    def reset(self) -> None:
        """Reset the state to start a new session."""

        self.segments.clear()
        self.pending_segment = None
        self.is_recording = False
        self.final_recording = None
        self.transcript = None
        self.speaker_labels.clear()

    def update_pending(self, segment_path: Optional[str]) -> None:
        """Update the pending segment with the latest audio file."""

        if segment_path and os.path.exists(segment_path):
            self.pending_segment = segment_path

    def update_label(self, speaker_id: str, label: str) -> None:
        """Add or update the display label for a speaker."""

        cleaned_label = label.strip()
        if cleaned_label:
            self.speaker_labels[speaker_id] = cleaned_label
        elif speaker_id in self.speaker_labels:
            del self.speaker_labels[speaker_id]

    def _combine_segments(self) -> str:
        """Combine the recorded audio segments into a single wave file."""

        if len(self.segments) == 1:
            return self._copy_single_segment(self.segments[0])

        final_path = os.path.join(
            tempfile.gettempdir(), f"meeting_recording_{next(tempfile._get_candidate_names())}.wav"
        )
        with wave.open(self.segments[0], "rb") as first_segment:
            params = first_segment.getparams()
            frames = [first_segment.readframes(first_segment.getnframes())]

        for segment_path in self.segments[1:]:
            with wave.open(segment_path, "rb") as segment:
                if segment.getparams()[:4] != params[:4]:
                    raise ValueError("All audio segments must share the same audio parameters")
                frames.append(segment.readframes(segment.getnframes()))

        with wave.open(final_path, "wb") as output:
            output.setparams(params)
            for chunk in frames:
                output.writeframes(chunk)
        return final_path

    @staticmethod
    def _copy_single_segment(segment_path: str) -> str:
        """Copy the lone audio segment into a deterministic location."""

        final_path = os.path.join(
            tempfile.gettempdir(), f"meeting_recording_{next(tempfile._get_candidate_names())}.wav"
        )
        shutil.copy(segment_path, final_path)
        return final_path
