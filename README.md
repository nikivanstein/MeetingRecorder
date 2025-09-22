# Meeting Recorder

A Gradio-based application for capturing meetings, transcribing the audio with
speaker identification, and generating concise summaries and action items.

## Features

- Record meetings directly in the browser with start, pause, resume, and stop controls.
- Transcribe the audio using AssemblyAI (or a deterministic offline fallback) with speaker diarisation.
- Relabel speakers after transcription to match participant names.
- Summarise the meeting and extract action items using OpenAI, Ollama, or an offline fallback.
- Persist the results to timestamped files and optionally email them to a configured recipient.

## Getting Started

1. Install dependencies (preferably within a virtual environment):

   ```bash
   pip install -r requirements.txt
   ```

   Alternatively, install editable:

   ```bash
   pip install -e .
   ```

2. Provide API keys as environment variables where available:

   - `ASSEMBLYAI_API_KEY` – AssemblyAI transcription service.
   - `OPENAI_API_KEY` – OpenAI model for summarisation.
   - `OLLAMA_BASE_URL` – URL of an Ollama instance to use instead of OpenAI.
   - SMTP settings (`SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`, `EMAIL_SENDER`, `MEETING_EMAIL_RECIPIENT`) for email delivery.

3. Launch the app:

   ```bash
   python -m meeting_recorder.app
   ```

   When the `GRADIO_SHARE` environment variable is set to `true`, a public Gradio
   share link is created automatically.

## Running Tests

```bash
pytest
```

## Project Structure

- `meeting_recorder/` – application source modules.
- `tests/` – unit tests.
- `meeting_outputs/` – default directory for saved meeting notes.

## Notes

- When API keys are not provided, the app falls back to deterministic dummy
  transcriptions and summaries to keep the UI functional for demonstrations and
  automated testing.
- Speaker relabelling is optional – edit the *Speaker Labels* table to change
  how diarised speakers appear in summaries and saved notes.
