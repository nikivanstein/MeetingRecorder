# MeetingRecorder

AI-based meeting notes assistant built with [Gradio](https://gradio.app/). The application lets you
record meetings directly from the browser, transcribe the audio with speaker identification, and
summarise the conversation with automated action items.

## Features

- Record audio from the microphone (with start, pause and stop controls) or upload existing files.
- Transcribe meetings via AssemblyAI with optional speaker label overrides.
- Summarise meetings and extract action items using OpenAI or an Ollama endpoint.
- Save the combined transcript, summary and action items to a text file.
- Optionally email the results to a pre-configured recipient.

## Getting started

1. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

2. Configure the required environment variables:

   - `ASSEMBLYAI_API_KEY`: API key used for transcription and diarisation.
   - `OPENAI_API_KEY` **or** `OLLAMA_ENDPOINT`: credentials used for the LLM summary step.
   - Optional email configuration when using SMTP delivery:
     - `MEETING_EMAIL_SENDER`
     - `MEETING_EMAIL_RECIPIENT`
     - `MEETING_SMTP_SERVER` (defaults to `localhost`)
     - `MEETING_SMTP_PORT` (defaults to `25`)
     - `MEETING_SMTP_USERNAME`
     - `MEETING_SMTP_PASSWORD`

3. Launch the Gradio interface:

   ```bash
   python main.py
   ```

   The UI provides buttons to start, pause and stop recording, a text box for optional speaker
   labels, and outputs for the transcript, summary and action items.

## Running tests

Unit tests validate the main orchestration logic and can be executed with:

```bash
pytest
```

## Notes

- The transcription and summarisation steps rely on external APIs; ensure the relevant credentials
  are available before running the app.
- Email delivery uses plain SMTP and will start a TLS session when credentials are provided.
