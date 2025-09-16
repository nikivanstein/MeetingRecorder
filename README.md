# MeetingRecorder

Python based application for recording, transcribing and summarizing meetings.

## Features

- Record meeting audio directly in the browser with options to start, pause and stop the capture.
- Transcribe meetings using [AssemblyAI](https://www.assemblyai.com/) with automatic speaker diarisation.
- Label speakers manually to make the transcript more readable.
- Summarise the meeting and extract action items using either OpenAI or a local Ollama model.
- Persist the generated notes to Markdown files and optionally email them to a configured recipient.

## Running the app

1. Install the Python dependencies:

   ```bash
   pip install -r requirements.txt
   ```

2. Export the required environment variables:

   - `ASSEMBLYAI_API_KEY` – required for transcription.
   - `OPENAI_API_KEY` – optional. Provides access to OpenAI's chat models.
   - `OPENAI_MODEL` – optional. Defaults to `gpt-3.5-turbo`.
   - `OLLAMA_MODEL` – optional. Use instead of OpenAI to target a local Ollama instance.
   - `MEETING_OUTPUT_DIR` – optional. Directory for generated Markdown files.
   - `EMAIL_SMTP_SERVER`, `EMAIL_SMTP_PORT`, `EMAIL_USERNAME`, `EMAIL_PASSWORD`,
     `EMAIL_FROM_ADDRESS`, `EMAIL_TO_ADDRESS`, `EMAIL_USE_TLS` – optional settings for the
     email integration.

3. Launch the Gradio interface:

   ```bash
   python -m meeting_recorder.app
   ```

4. Record the meeting, stop the recording and click **Transcribe & Summarise** to process
   the audio. Download the generated Markdown file or tick *Email the summary* to send
   it to the configured address.

## Tests

Unit tests can be executed with `pytest`:

```bash
pytest
```
