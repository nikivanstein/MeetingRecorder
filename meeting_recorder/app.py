"""Gradio application entry point for the meeting recorder."""

from __future__ import annotations

import os
from typing import Dict, Iterable, List, Optional

from .emailer import EmailClient
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
    if label_rows.empty() or not label_rows:
        return label_map
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
        owner = item.get("owner", "Unassigned")
        description = item.get("description", "")
        if description:
            lines.append(f"- **{owner}**: {description}")
    return "\n".join(lines) or "No action items detected."


class MeetingRecorderApp:
    """Encapsulates UI wiring and backend integrations."""

    def __init__(self) -> None:
        if gr is None:
            raise RuntimeError("Gradio is required to launch the Meeting Recorder UI. Install the optional dependencies.")
        self.transcriber: Transcriber = get_transcriber()
        self.summariser: Summariser = get_summariser()
        self.email_client = EmailClient.from_env()
        self.interface = self._build_interface()

    def _build_interface(self) -> gr.Blocks:
        with gr.Blocks(title="Meeting Recorder") as demo:
            gr.Markdown(
                """# Meeting Recorder & Summariser\n"""
                "Record meetings, transcribe with speaker identification, and generate concise notes."
            )
            audio = gr.Audio(
                sources=["microphone"],
                type="filepath",
                streaming=False,
                #waveform_options={"show_recording_duration": True},
                label="Meeting Recorder",
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

            transcription_state = gr.State()
            summary_state = gr.State()

            status = gr.Markdown("Ready to record.")
            transcribe_btn = gr.Button("Transcribe Recording", variant="primary")
            transcript_text = gr.Textbox(label="Transcript", lines=8)
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
                inputs=[audio],
                outputs=[
                    transcription_state,
                    transcript_text,
                    segments_df,
                    speaker_label_df,
                    status,
                ],
            )

            summarise_btn = gr.Button("Summarise & Extract Actions", variant="secondary")
            summary_markdown = gr.Markdown(label="Meeting Summary")
            actions_markdown = gr.Markdown(label="Action Items")

            summarise_btn.click(
                self.summarise,
                inputs=[transcription_state, speaker_label_df],
                outputs=[summary_markdown, actions_markdown, summary_state, status],
            )

            with gr.Row():
                send_email = gr.Checkbox(label=self._email_label(), value=False)
                save_btn = gr.Button("Save Results", variant="secondary")
            saved_file = gr.File(label="Saved Meeting Notes")

            save_btn.click(
                self.save,
                inputs=[transcription_state, summary_state, send_email],
                outputs=[saved_file, status],
            )

            gr.Markdown(
                """Configure API keys via environment variables such as ``ASSEMBLYAI_API_KEY`` and ``OPENAI_API_KEY``."""
            )
        return demo

    def _email_label(self) -> str:
        if self.email_client:
            return f"Email results to {self.email_client.config.recipient}"
        return "Email results (configure SMTP via environment variables)"

    def launch(self, **kwargs: object) -> gr.Blocks:
        """Expose the underlying Gradio interface to callers."""

        self.interface.queue()
        if os.environ.get("GRADIO_SHARE", "false").lower() in {"1", "true", "yes"}:
            kwargs.setdefault("share", True)
        self.interface.launch(**kwargs)
        return self.interface

    def transcribe(self, audio_path: Optional[str]):
        if not audio_path:
            return None, "", [], [], "Please record audio before transcribing."
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

    def summarise(self, payload: Optional[Dict[str, object]], label_rows: Optional[List[List[str]]]):
        if not payload:
            return "", "", None, "Transcribe the recording before summarising."
        transcription = TranscriptionResult.from_payload(payload)
        labels = build_label_map(label_rows)
        labelled = transcription.apply_labels(labels) if labels else transcription
        summary = self.summariser.summarise(labelled)
        summary_md = summary.get("summary", "Summary unavailable.")
        action_md = format_action_items(summary.get("action_items", []))
        return summary_md, action_md, summary, "Summary generated successfully."

    def save(
        self,
        payload: Optional[Dict[str, object]],
        summary_payload: Optional[Dict[str, object]],
        send_email: bool,
    ):
        if not payload:
            return None, "Please transcribe and summarise the meeting before saving."
        transcription = TranscriptionResult.from_payload(payload)
        summary = summary_payload or {"summary": transcription.text, "action_items": []}
        file_path = save_meeting_artifacts(transcription, summary)
        status = f"Results saved to {file_path}."
        if send_email:
            if self.email_client:
                try:
                    self.email_client.send(
                        subject="Meeting Notes",
                        body="Please find the meeting notes attached.",
                        attachment=file_path,
                    )
                    status += " Email sent successfully."
                except Exception as exc:  # pragma: no cover - network failure guard
                    status += f" Email delivery failed: {exc}."
            else:
                status += " Email configuration not available."
        return str(file_path), status


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
