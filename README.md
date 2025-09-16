# Meeting Recorder

A self-hosted meeting assistant that records audio, transcribes the conversation with
speaker diarisation, generates summaries and action items using an LLM, and lets you
export the results.

## Features

- Web UI for starting, pausing, resuming, and stopping audio recordings in the browser.
- Transcription with speaker identification powered by [AssemblyAI](https://www.assemblyai.com/).
- Meeting summary and action item extraction using [OpenAI](https://openai.com/) models.
- Optional speaker relabelling directly in the UI.
- Export meeting notes to disk or email them via SMTP.

## Requirements

- Python 3.10+
- Node is **not** required; the UI is pure HTML/CSS/JavaScript served by Flask.
- AssemblyAI and OpenAI API keys.
- Optional SMTP credentials if you want to email meeting notes.

## Quick start

1. Create and activate a virtual environment.

   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```

2. Install dependencies.

   ```bash
   pip install -r requirements.txt
   ```

3. Export the required environment variables:

   ```bash
   export ASSEMBLYAI_API_KEY="<your-assemblyai-key>"
   export OPENAI_API_KEY="<your-openai-key>"
   # Optional overrides
   export OPENAI_MODEL="gpt-4o-mini"
   export EMAIL_ENABLED=true
   export SMTP_SERVER="smtp.example.com"
   export SMTP_PORT=587
   export SMTP_USERNAME="bot@example.com"
   export SMTP_PASSWORD="<smtp-password>"
   export EMAIL_SENDER="bot@example.com"
   export EMAIL_RECIPIENT="product@example.com"
   ```

   Omit the email-related settings if you do not need email delivery.

4. Run the development server.

   ```bash
   flask --app app.main run --debug
   ```

   Visit <http://127.0.0.1:5000/> to open the interface. Grant the browser access to
your microphone, record the meeting, and wait for the transcription and summary.

5. Export the meeting results to disk or send them via email from the UI.

## Testing

Run the automated tests with `pytest`:

```bash
pytest
```

## Architecture overview

- `app/main.py`: Flask application wiring, request handlers, and service composition.
- `app/services/`: Service layer for transcription, LLM summarisation, formatting, and email.
- `static/` and `templates/`: Front-end assets served by Flask.
- `tests/`: Unit tests covering formatting helpers and the email sender.

## Notes

- The transcription and summarisation steps require internet access to reach AssemblyAI
  and OpenAI.
- Recordings are stored under `data/recordings/` and exported notes are saved under
  `data/results/`.
- When emailing results the SMTP server must support STARTTLS if `SMTP_USE_TLS` is left
  at its default value of `true`.
