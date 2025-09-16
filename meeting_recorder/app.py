"""Gradio user interface for the Meeting Recorder application."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict, List, Tuple

import gradio as gr

from .config import AppConfig
from .emailer import send_email_with_summary
from .storage import save_meeting_result
from .summarizer import LLMSummarizer, MeetingSummary
from .transcription import TranscriptionResult, parse_speaker_labels, transcribe_audio

LOGGER = logging.getLogger(__name__)


def _format_summary_markdown(summary: MeetingSummary) -> str:
    lines = ["## Summary"]
    lines.append(summary.summary or "No summary generated.")
    return "\n\n".join(lines)


def _format_action_markdown(action_items: List[str]) -> str:
    lines = ["## Action Items"]
    if action_items:
        lines.extend(f"- {item}" for item in action_items)
    else:
        lines.append("- No action items identified.")
    return "\n".join(lines)


def _process_meeting(
    audio_path: str | None,
    speaker_label_text: str,
    send_email: bool,
    config: AppConfig,
    summarizer: LLMSummarizer,
) -> Tuple[str, str, str, str, str | None]:
    """Handle the end-to-end meeting processing workflow."""

    if not audio_path:
        message = "⚠️ No audio captured. Please record the meeting before processing."
        return "", "", "", message, None

    try:
        labels: Dict[str, str] = parse_speaker_labels(speaker_label_text)
        transcription: TranscriptionResult = transcribe_audio(audio_path, config, labels)
        summary: MeetingSummary = summarizer.summarise(transcription.text)
        output_path: Path = save_meeting_result(transcription, summary, config.output_dir)
    except Exception as exc:  # pragma: no cover - exercised through UI only
        LOGGER.exception("Failed to process meeting")
        return "", "", "", f"❌ Error: {exc}", None

    email_message = ""
    if send_email:
        try:
            body_lines = [summary.summary or "No summary generated.", "", "Action items:"]
            body_lines.extend(summary.action_items or ["No action items identified."])
            email_body = "\n".join(body_lines)
            send_email_with_summary(
                config.email,
                subject="Automated meeting notes",
                body=email_body,
                attachment=output_path,
            )
            email_message = " Email sent to configured recipient."
        except Exception as exc:  # pragma: no cover - network interaction
            LOGGER.exception("Failed to send email")
            email_message = f" Email delivery failed: {exc}."

    transcription_markdown = transcription.format_markdown()
    summary_markdown = _format_summary_markdown(summary)
    action_markdown = _format_action_markdown(summary.action_items)
    status_message = f"✅ Meeting processed. Notes saved to {output_path}.{email_message}"

    return (
        transcription_markdown,
        summary_markdown,
        action_markdown,
        status_message,
        str(output_path),
    )


def build_app() -> gr.Blocks:
    """Create the Gradio Blocks application."""

    logging.basicConfig(level=logging.INFO)
    config = AppConfig.from_env()
    summarizer = LLMSummarizer(config)

    with gr.Blocks(title="Meeting Recorder") as demo:
        gr.Markdown(
            """
            # Meeting Recorder
            Record meetings, transcribe them with speaker diarisation and extract action items.
            """
        )

        recording_state = gr.State(False)
        status_output = gr.Markdown("Ready to record.")

        with gr.Row():
            audio_input = gr.Audio(
                label="Meeting audio",
                sources=["microphone", "upload"],
                type="filepath",
            )

        with gr.Row():
            start_button = gr.Button("Start Recording", variant="primary")
            pause_button = gr.Button("Pause Recording")
            stop_button = gr.Button("Stop Recording")

        def start_recording(_: bool) -> Tuple[bool, str]:
            return True, "Recording started. Use the audio widget to speak."  # pragma: no cover

        def pause_recording(is_recording: bool) -> Tuple[bool, str]:
            if is_recording:
                return False, "Recording paused. Resume by pressing start."
            return False, "Recording is not active."  # pragma: no cover

        def stop_recording(_: bool) -> Tuple[bool, str]:
            return False, "Recording stopped. You can now process the meeting."

        start_button.click(start_recording, inputs=recording_state, outputs=[recording_state, status_output])
        pause_button.click(pause_recording, inputs=recording_state, outputs=[recording_state, status_output])
        stop_button.click(stop_recording, inputs=recording_state, outputs=[recording_state, status_output])

        speaker_label_input = gr.Textbox(
            label="Speaker labels (optional)",
            placeholder="Speaker A=Alice\nSpeaker B=Bob",
            lines=2,
        )
        send_email_checkbox = gr.Checkbox(label="Email the summary", value=False)

        process_button = gr.Button("Transcribe & Summarise", variant="primary")

        transcription_output = gr.Markdown(label="Transcript")
        summary_output = gr.Markdown(label="Summary")
        action_output = gr.Markdown(label="Action Items")
        file_output = gr.File(label="Saved meeting notes")

        process_button.click(
            fn=lambda audio, labels, email: _process_meeting(
                audio, labels, email, config, summarizer
            ),
            inputs=[audio_input, speaker_label_input, send_email_checkbox],
            outputs=[
                transcription_output,
                summary_output,
                action_output,
                status_output,
                file_output,
            ],
        )

    return demo


if __name__ == "__main__":
    build_app().launch()
