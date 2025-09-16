"""Gradio application that orchestrates meeting recording and summarisation."""

from __future__ import annotations

import json
from typing import Dict, Optional

import gradio as gr

from .config import get_settings
from .notifier import EmailNotifier, ResultSaver
from .state import MeetingState
from .summarizer import LLMSummarizer, SummarizationError
from .transcription import AssemblyAITranscriber, TranscriptionError


def create_app() -> gr.Blocks:
    """Create and return the Gradio Blocks application."""

    settings = get_settings()
    saver = ResultSaver()

    with gr.Blocks(title="Meeting Recorder") as demo:
        gr.Markdown(
            """
            # Meeting Recorder
            Record meetings, transcribe the conversation with speaker identification, and
            automatically produce summaries and action items.
            """
        )

        state = gr.State(MeetingState())

        with gr.Row():
            audio_input = gr.Audio(
                sources=["microphone", "upload"],
                type="filepath",
                label="Meeting audio",
            )
            final_audio = gr.Audio(label="Final recording", interactive=False)

        status = gr.Markdown("Ready to record.")

        with gr.Row():
            start_btn = gr.Button("Start Recording", variant="primary")
            pause_btn = gr.Button("Pause Recording")
            stop_btn = gr.Button("Stop Recording", variant="stop")

        speaker_labels = gr.Textbox(
            label="Optional speaker labels (JSON dictionary)",
            placeholder='{"A": "Alice", "B": "Bob"}',
        )

        transcribe_btn = gr.Button("Transcribe & Summarise", variant="primary")

        transcript_output = gr.Textbox(label="Transcript", lines=10)
        summary_output = gr.Textbox(label="Summary", lines=6)
        action_output = gr.Textbox(label="Action Items", lines=6)

        with gr.Row():
            email_checkbox = gr.Checkbox(label="Email results to preset recipient?", value=False)
            save_btn = gr.Button("Save Results", variant="secondary")
        save_status = gr.Markdown()

        def on_audio_change(audio_path: Optional[str], state_value: MeetingState):
            state_value.update_pending(audio_path)
            message = (
                "Captured an audio segment. Click *Pause* to queue it or *Stop* to finalise "
                "the recording."
                if audio_path
                else "Waiting for audio input."
            )
            return state_value, message

        def on_start(state_value: MeetingState):
            state_value.start()
            state_value.final_recording = None
            state_value.transcript = None
            return (
                state_value,
                "Recording started. Use the microphone widget and then pause or stop when ready.",
                gr.update(value=None, interactive=True),
                gr.update(value=None),
            )

        def on_pause(state_value: MeetingState, audio_path: Optional[str]):
            state_value.pause(audio_path)
            return (
                state_value,
                "Recording paused. Record another segment or press stop to finish.",
                gr.update(value=None),
                gr.update(value=state_value.final_recording),
            )

        def on_stop(state_value: MeetingState, audio_path: Optional[str]):
            try:
                final_path = state_value.stop(audio_path)
            except ValueError as exc:
                raise gr.Error(str(exc)) from exc
            if not final_path:
                message = "No audio captured yet. Please record before stopping."
            else:
                message = "Recording complete. You can now transcribe the meeting."
            return (
                state_value,
                message,
                gr.update(value=None),
                gr.update(value=final_path) if final_path else gr.update(value=None),
            )

        def parse_labels(raw: str) -> Dict[str, str]:
            if not raw or not raw.strip():
                return {}
            try:
                data = json.loads(raw)
            except json.JSONDecodeError as exc:  # pragma: no cover - user input
                raise gr.Error("Speaker labels must be valid JSON") from exc
            if not isinstance(data, dict):
                raise gr.Error("Speaker labels must be provided as a JSON object")
            return {str(key): str(value) for key, value in data.items() if str(value).strip()}

        def ensure_transcriber() -> AssemblyAITranscriber:
            if not settings.assemblyai_api_key:
                raise gr.Error("Set the ASSEMBLYAI_API_KEY environment variable to transcribe audio.")
            return AssemblyAITranscriber(settings.assemblyai_api_key)

        def ensure_summarizer() -> LLMSummarizer:
            try:
                return LLMSummarizer(
                    openai_api_key=settings.openai_api_key,
                    ollama_endpoint=settings.ollama_endpoint,
                )
            except ValueError as exc:
                raise gr.Error(
                    "Configure either the OPENAI_API_KEY or OLLAMA_ENDPOINT environment variable to "
                    "enable summarisation."
                ) from exc

        def on_transcribe(state_value: MeetingState, labels_text: str):
            if not state_value.final_recording:
                raise gr.Error("Please stop the recording before starting transcription.")
            label_mapping = parse_labels(labels_text)
            state_value.speaker_labels.update(label_mapping)
            transcriber = ensure_transcriber()
            summarizer = ensure_summarizer()
            try:
                transcript = transcriber.transcribe(state_value.final_recording, state_value.speaker_labels)
                summary_payload = summarizer.summarize(transcript.as_text())
            except (TranscriptionError, SummarizationError) as exc:
                raise gr.Error(str(exc)) from exc
            transcript.summary = summary_payload.get("summary", "")
            transcript.action_items = summary_payload.get("action_items", "")
            state_value.transcript = transcript
            return (
                state_value,
                transcript.as_text(),
                transcript.summary,
                transcript.action_items,
                "Transcription and summarisation complete.",
            )

        def on_save(state_value: MeetingState, should_email: bool):
            if not state_value.transcript:
                raise gr.Error("Nothing to save. Please transcribe the meeting first.")
            saved_path = saver.save(state_value.transcript)
            message = f"Saved meeting notes to {saved_path}."
            if should_email:
                if not settings.email_sender or not settings.email_recipient:
                    raise gr.Error(
                        "Email settings are incomplete. Provide MEETING_EMAIL_SENDER and "
                        "MEETING_EMAIL_RECIPIENT environment variables."
                    )
                notifier = EmailNotifier(
                    sender=settings.email_sender,
                    recipient=settings.email_recipient,
                    smtp_server=settings.smtp_server,
                    smtp_port=settings.smtp_port,
                    username=settings.smtp_username,
                    password=settings.smtp_password,
                )
                try:
                    notifier.send(state_value.transcript, saved_path)
                    message += " Email sent successfully."
                except Exception as exc:  # pragma: no cover - depends on SMTP configuration
                    raise gr.Error(f"Failed to send email: {exc}") from exc
            return message

        audio_input.change(on_audio_change, inputs=[audio_input, state], outputs=[state, status])
        start_btn.click(on_start, inputs=[state], outputs=[state, status, audio_input, final_audio])
        pause_btn.click(on_pause, inputs=[state, audio_input], outputs=[state, status, audio_input, final_audio])
        stop_btn.click(on_stop, inputs=[state, audio_input], outputs=[state, status, audio_input, final_audio])
        transcribe_btn.click(
            on_transcribe,
            inputs=[state, speaker_labels],
            outputs=[state, transcript_output, summary_output, action_output, status],
        )
        save_btn.click(on_save, inputs=[state, email_checkbox], outputs=[save_status])

    return demo
