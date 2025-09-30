import datetime as dt
import json
from pathlib import Path

import pytest

from meeting_recorder.models import SpeakerSegment, TranscriptionResult
from meeting_recorder.templates import (
    MeetingTemplate,
    build_template_context,
    get_meeting_template,
    render_template_for_prompt,
)


@pytest.fixture()
def transcript() -> TranscriptionResult:
    segments = [
        SpeakerSegment(speaker="A", start=0, end=30, text="Intro"),
        SpeakerSegment(speaker="B", start=30, end=90, text="Discussion"),
    ]
    return TranscriptionResult(segments=segments)


def test_build_template_context_uses_now(transcript: TranscriptionResult) -> None:
    now = dt.datetime(2024, 6, 1, 12, 30, tzinfo=dt.timezone.utc)
    context = build_template_context(transcript, now=now)
    assert context["meeting_date"] == "2024-06-01"
    assert context["generated_timestamp"] == "2024-06-01 12:30"
    assert context["time_range"] == "00:00 – 00:01"


def test_render_template_for_prompt_injects_times(transcript: TranscriptionResult) -> None:
    now = dt.datetime(2024, 6, 1, 12, 30, tzinfo=dt.timezone.utc)
    rendered = render_template_for_prompt(transcript, now=now)
    assert "2024-06-01" in rendered
    assert "00:00 – 00:01" in rendered


def test_get_meeting_template_reads_custom_file(tmp_path: Path) -> None:
    custom_path = tmp_path / "custom_templates.json"
    custom_path.write_text(
        json.dumps(
            {
                "default": "custom",
                "templates": [
                    {
                        "id": "custom",
                        "name": "Custom",
                        "content": "Report {meeting_date} {meeting_start} {meeting_end}",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    template = get_meeting_template(config_path=custom_path)
    assert isinstance(template, MeetingTemplate)
    rendered = template.render(
        {
            "meeting_date": "2024-01-01",
            "meeting_start": "09:00",
            "meeting_end": "10:00",
            "time_range": "09:00 – 10:00",
            "generated_timestamp": "2024-01-01 10:00",
        }
    )
    assert "Report 2024-01-01 09:00 10:00" == rendered
