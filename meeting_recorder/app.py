"""Gradio application entry point for the meeting recorder."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, Iterable, List, Optional
from .models import SpeakerSegment, TranscriptionResult
from .storage import save_meeting_artifacts
from .summarizer import Summariser, get_summariser
from .transcriber import Transcriber, get_transcriber


try:
    import gradio as gr
except ModuleNotFoundError:  # pragma: no cover - allows docs/tests without gradio
    gr = None  # type: ignore

def build_label_map(label_rows: Optional[List[List[str]]]) -> Dict[str, str]:
    """Create a mapping from diarised speaker identifiers to user supplied labels."""

    label_map: Dict[str, str] = {}
    for row in label_rows:
        if not row or len(row) < 2:
            continue
        diarised_id, custom_label = row[0], row[1]
        if diarised_id:
            label_map[str(diarised_id)] = custom_label or str(diarised_id)
    return label_map


def format_segments_table(segments: Iterable[SpeakerSegment]) -> List[List[str]]:
    rows: List[List[str]] = []
    for segment in segments:
        rows.append(
            [
                segment.speaker,
                _format_ts(segment.start),
                _format_ts(segment.end),
                segment.text,
            ]
        )
    return rows


def _format_ts(value: float) -> str:
    minutes, seconds = divmod(int(value), 60)
    return f"{minutes:02d}:{seconds:02d}"


def format_action_items(action_items: Iterable[Dict[str, str]]) -> str:
    lines = []
    for item in action_items:
        owner = (item.get("owner") or "Unassigned").strip() or "Unassigned"
        description = (item.get("description") or "").strip()
        if description:
            lines.append(f"- {owner}: {description}")
    return "\n".join(lines) or "No action items detected."


class MeetingRecorderApp:
    """Encapsulates UI wiring and backend integrations."""

    def __init__(self) -> None:
        if gr is None:
            raise RuntimeError("Gradio is required to launch the Meeting Recorder UI. Install the optional dependencies.")
        self.transcriber: Transcriber = get_transcriber()
        self.summariser: Summariser = get_summariser()
        self.interface = self._build_interface()

    def _build_interface(self) -> gr.Blocks:
        with gr.Blocks(title="Meeting Recorder") as demo:
            gr.Markdown(
                """# Meeting Recorder & Summariser\n"""
                "Record meetings, transcribe with speaker identification, and generate concise notes."
            )
            audio = gr.Audio(
                sources=["microphone", "upload"],
                type="filepath",
                streaming=False,
                #waveform_options={"show_recording_duration": True},
                label="Meeting Recorder",
            )
            recording_state = gr.State()
            transcription_state = gr.State()
            summary_state = gr.State()
            recording_file = gr.File(label="Download Recording", interactive=False, visible=False)

            audio.change(
                self.store_recording,
                inputs=[audio],
                outputs=[recording_state, recording_file],
            )
            with gr.Row():
                start_btn = gr.Button("Start Recording", elem_id="start-recording")
                pause_btn = gr.Button("Pause", elem_id="pause-recording")
                resume_btn = gr.Button("Resume", elem_id="resume-recording")
                stop_btn = gr.Button("Stop", elem_id="stop-recording")

            start_btn.click(fn=None, inputs=None, outputs=None, js=_JS_START_RECORDING)
            pause_btn.click(fn=None, inputs=None, outputs=None, js=_JS_PAUSE_RECORDING)
            resume_btn.click(fn=None, inputs=None, outputs=None, js=_JS_RESUME_RECORDING)
            stop_btn.click(fn=None, inputs=None, outputs=None, js=_JS_STOP_RECORDING)

            status = gr.Markdown("Ready to record or upload audio.")
            transcribe_btn = gr.Button("Transcribe Recording", variant="primary")
            transcript_text = gr.Textbox(label="Transcript", lines=8)
            transcript_upload = gr.File(
                label="Upload Transcript",
                file_types=["text", ".md", ".txt"],
                type="filepath",
            )
            segments_df = gr.Dataframe(
                headers=["Speaker", "Start", "End", "Text"],
                datatype=["str", "str", "str", "str"],
                interactive=False,
                label="Diarised Segments",
            )
            speaker_label_df = gr.Dataframe(
                headers=["Speaker", "Label"],
                datatype=["str", "str"],
                label="Speaker Labels",
                interactive=True,
            )

            transcribe_btn.click(
                self.transcribe,
                inputs=[recording_state],
                outputs=[
                    transcription_state,
                    transcript_text,
                    segments_df,
                    speaker_label_df,
                    status,
                ],
            )

            transcript_upload.change(
                self.load_transcript,
                inputs=[transcript_upload],
                outputs=[
                    transcription_state,
                    transcript_text,
                    segments_df,
                    speaker_label_df,
                    status,
                ],
            )

            summarise_btn = gr.Button("Summarise & Extract Actions", variant="secondary")
            summary_text = gr.Textbox(label="Meeting Summary", lines=8)
            actions_text = gr.Textbox(label="Action Items", lines=6)
            saved_summary_file = gr.File(
                label="Saved Meeting Notes", interactive=False, visible=False
            )
            saved_transcript_file = gr.File(
                label="Saved Transcript", interactive=False, visible=False
            )

            summarise_btn.click(
                self.summarise,
                inputs=[transcription_state, speaker_label_df],
                outputs=[
                    summary_text,
                    actions_text,
                    summary_state,
                    status,
                    saved_summary_file,
                    saved_transcript_file,
                ],
            )

            gr.Markdown(
                """Configure API keys via environment variables such as ``ASSEMBLYAI_API_KEY`` and ``OPENAI_API_KEY``."""
            )
        return demo

    def launch(self, **kwargs: object) -> gr.Blocks:
        """Expose the underlying Gradio interface to callers."""

        self.interface.queue()
        if os.environ.get("GRADIO_SHARE", "false").lower() in {"1", "true", "yes"}:
            kwargs.setdefault("share", True)
        self.interface.launch(**kwargs)
        return self.interface

    def transcribe(self, audio_path: Optional[str]):
        if not audio_path:
            return None, "", [], [], "Please record or upload audio before transcribing."
        result = self.transcriber.transcribe(audio_path)
        payload = result.to_payload()
        transcript_text = result.text
        segments_table = format_segments_table(result.segments)
        unique_speakers = []
        for segment in result.segments:
            if segment.speaker not in unique_speakers:
                unique_speakers.append(segment.speaker)
        label_table = [[speaker, speaker] for speaker in unique_speakers]
        return payload, transcript_text, segments_table, label_table, "Transcription complete."

    def load_transcript(self, transcript_path: Optional[str]):
        if not transcript_path:
            message = "Select a transcript file to load."
            return None, "", [], [], message
        path = Path(transcript_path)
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError as exc:
            return None, "", [], [], f"Failed to read transcript: {exc}"
        stripped = text.strip()
        if not stripped:
            return None, "", [], [], f"{path.name} is empty."
        segments: List[SpeakerSegment] = []
        for idx, raw_line in enumerate(text.splitlines()):
            line = raw_line.strip()
            if not line:
                continue
            speaker = "Transcript"
            content = line
            if ":" in line:
                potential_speaker, remainder = line.split(":", 1)
                if potential_speaker.strip() and remainder.strip():
                    speaker = potential_speaker.strip()
                    content = remainder.strip()
            segments.append(
                SpeakerSegment(
                    speaker=speaker,
                    start=float(idx),
                    end=float(idx + 1),
                    text=content,
                )
            )
        if not segments:
            segments.append(
                SpeakerSegment(speaker="Transcript", start=0.0, end=0.0, text=stripped)
            )
        result = TranscriptionResult(segments=segments)
        payload = result.to_payload()
        segments_table = format_segments_table(result.segments)
        unique_speakers: List[str] = []
        for segment in result.segments:
            if segment.speaker not in unique_speakers:
                unique_speakers.append(segment.speaker)
        label_table = [[speaker, speaker] for speaker in unique_speakers]
        status = f"Loaded transcript from {path.name}."
        return payload, text, segments_table, label_table, status

    def summarise(
        self,
        payload: Optional[Dict[str, object]],
        label_rows: Optional[List[List[str]]],
    ):
        empty_files = (
            gr.update(value=None, visible=False),
            gr.update(value=None, visible=False),
        )
        if not payload:
            return (
                "",
                "",
                None,
                "Transcribe or upload a transcript before summarising.",
                *empty_files,
            )
        transcription = TranscriptionResult.from_payload(payload)
        labels = build_label_map(label_rows)
        labelled = transcription.apply_labels(labels) if labels else transcription
        summary = self.summariser.summarise(labelled)
        summary_text = str(summary.get("summary", "Summary unavailable."))
        actions_text = format_action_items(summary.get("action_items", []))
        artifacts = save_meeting_artifacts(labelled, summary)
        status_message = (
            "Summary generated successfully. "
            f"Results saved to {artifacts.summary_path}. "
            f"Transcript saved to {artifacts.transcript_path}."
        )
        return (
            summary_text,
            actions_text,
            summary,
            status_message,
            gr.update(value=str(artifacts.summary_path), visible=True),
            gr.update(value=str(artifacts.transcript_path), visible=True),
        )

    def store_recording(self, audio_path: Optional[str]):
        if not audio_path:
            return None, gr.update(value=None, visible=False)
        return audio_path, gr.update(value=audio_path, visible=True)

    def save(
        self,
        payload: Optional[Dict[str, object]],
        summary_payload: Optional[Dict[str, object]],
    ):
        if not payload:
            return None, None, "Please provide a transcript before saving."
        transcription = TranscriptionResult.from_payload(payload)
        summary = summary_payload or {"summary": transcription.text, "action_items": []}
        artifacts = save_meeting_artifacts(transcription, summary)
        status = (
            f"Results saved to {artifacts.summary_path}. "
            f"Transcript saved to {artifacts.transcript_path}."
        )
        return str(artifacts.summary_path), str(artifacts.transcript_path), status


def create_app() -> MeetingRecorderApp:
    """Factory for convenience when launching via ``python -m``."""

    return MeetingRecorderApp()


_JS_START_RECORDING = """
() => {
  const app = gradioApp();
  const audio = app.querySelector('audio, gradio-audio') || app.querySelector('gradio-audio');
  const recordBtn = app.querySelector('button[aria-label="Start Recording"]') || app.querySelector('button[aria-label="Record audio"]');
  if (recordBtn) { recordBtn.click(); }
  return [];
}
"""

_JS_PAUSE_RECORDING = """
() => {
  const app = gradioApp();
  const pauseBtn = app.querySelector('button[aria-label="Pause Recording"]');
  if (pauseBtn) { pauseBtn.click(); }
  return [];
}
"""

_JS_RESUME_RECORDING = """
() => {
  const app = gradioApp();
  const resumeBtn = app.querySelector('button[aria-label="Resume Recording"]');
  if (resumeBtn) { resumeBtn.click(); }
  return [];
}
"""

_JS_STOP_RECORDING = """
() => {
  const app = gradioApp();
  const stopBtn = app.querySelector('button[aria-label="Stop Recording"]') || app.querySelector('button[aria-label="Stop"]');
  if (stopBtn) { stopBtn.click(); }
  return [];
}
"""


__all__ = ["MeetingRecorderApp", "create_app"]


if __name__ == "__main__":
    create_app().launch()
