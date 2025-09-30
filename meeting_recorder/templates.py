"""Meeting minutes template helpers."""

from __future__ import annotations

import datetime as _dt
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, Mapping, MutableMapping, Optional, Tuple

from .models import SpeakerSegment, TranscriptionResult


DEFAULT_TEMPLATE_ID = "meeting_minutes"

_DEFAULT_TEMPLATE_TEXT = """# Meeting Minutes\n\n**Title:** [Meeting Title]\n**Date:** {meeting_date}\n**Time:** {time_range}\n**Location/Platform:** [Zoom / Office / etc.]\n**Participants:** [Name 1, Name 2, Name 3]\n**Moderator:** [Name]\n**Recorder:** [Name]\n\n---\n\n## Summary\n[One-paragraph overview of meeting purpose and main outcomes.]\n\n---\n\n## Decisions\n- [Decision 1 — short, clear sentence]\n- [Decision 2]\n- [Decision 3]\n\n---\n\n## Action Points\n| ID | Action Item | Responsible | Deadline | Status |\n|----|-------------|-------------|----------|--------|\n| AP-1 | [Description] | [Name] | [YYYY-MM-DD] | Open |\n| AP-2 | [Description] | [Name] | [YYYY-MM-DD] | Open |\n\n---\n\n## Topics Discussed\n\n### Topic 1: [Title]\n- **Discussion Summary:**\n  [Key points of discussion]\n- **Related Decisions:**\n  - [Decision]\n- **Follow-ups:**\n  - [Action or open issue]\n\n### Topic 2: [Title]\n- **Discussion Summary:**\n  [Key points of discussion]\n- **Related Decisions:**\n  - [Decision]\n- **Follow-ups:**\n  - [Action or open issue]\n\n---\n\n## Next Meeting\n- **Proposed Date/Time:** [YYYY-MM-DD, HH:MM]\n- **Tentative Agenda:**\n  - [Item 1]\n  - [Item 2]\n\n---\n\n**Document Generated:** {generated_timestamp}\n"""


@dataclass(frozen=True)
class MeetingTemplate:
    """Container for a meeting template definition."""

    identifier: str
    name: str
    content: str

    def render(self, context: Mapping[str, str]) -> str:
        """Render the template with the provided ``context`` mapping."""

        return _safe_format(self.content, context)


def get_meeting_template(
    template_id: Optional[str] = None,
    *,
    config_path: str | Path | None = None,
) -> MeetingTemplate:
    """Return the configured :class:`MeetingTemplate`.

    Templates are loaded from JSON files with the structure::

        {
            "default": "meeting_minutes",
            "templates": [
                {"id": "meeting_minutes", "name": "Meeting Minutes", "content": "..."}
            ]
        }

    The path may be configured via the ``MEETING_TEMPLATE_FILE`` environment variable.
    If the file is missing or invalid a built-in default template is used.
    """

    registry, default_id = _load_template_registry(config_path)
    selected_id = template_id or os.environ.get("MEETING_TEMPLATE_ID") or default_id
    template = registry.get(selected_id)
    if template is None and registry:
        template = registry[next(iter(registry))]
    return template or _default_template()


def render_template_for_prompt(
    transcript: TranscriptionResult,
    template: Optional[MeetingTemplate] = None,
    *,
    now: Optional[_dt.datetime] = None,
) -> str:
    """Return the meeting template with timestamps filled for prompt usage."""

    template = template or get_meeting_template()
    context = build_template_context(transcript, now=now)
    return template.render(context)


def build_template_context(
    transcript: TranscriptionResult,
    *,
    now: Optional[_dt.datetime] = None,
) -> Dict[str, str]:
    """Return values used to populate dynamic fields within a template."""

    current = now or _dt.datetime.now(tz=_dt.timezone.utc)
    meeting_date = current.date().isoformat()
    generated_timestamp = current.strftime("%Y-%m-%d %H:%M")
    start_seconds, end_seconds = _calculate_start_end(transcript.segments)
    start_label = _format_clock_time(start_seconds)
    end_label = _format_clock_time(end_seconds)
    time_range = f"{start_label} – {end_label}"
    return {
        "meeting_date": meeting_date,
        "generated_timestamp": generated_timestamp,
        "time_range": time_range,
        "meeting_start": start_label,
        "meeting_end": end_label,
    }


def _load_template_registry(
    config_path: str | Path | None,
) -> Tuple[Dict[str, MeetingTemplate], str]:
    path = _resolve_config_path(config_path)
    if path is None:
        return _default_registry()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return _default_registry()
    templates: Dict[str, MeetingTemplate] = {}
    for item in data.get("templates", []):
        identifier = item.get("id")
        content = item.get("content")
        name = item.get("name") or identifier
        if not identifier or not isinstance(identifier, str):
            continue
        if not content or not isinstance(content, str):
            continue
        templates[identifier] = MeetingTemplate(identifier=identifier, name=str(name or identifier), content=content)
    if not templates:
        return _default_registry()
    default_id = data.get("default")
    if not default_id or default_id not in templates:
        default_id = next(iter(templates))
    return templates, default_id


def _resolve_config_path(config_path: str | Path | None) -> Optional[Path]:
    if config_path:
        return Path(config_path)
    env_path = os.environ.get("MEETING_TEMPLATE_FILE")
    if env_path:
        return Path(env_path)
    bundled = Path(__file__).with_name("meeting_templates.json")
    if bundled.exists():
        return bundled
    return None


def _default_registry() -> Tuple[Dict[str, MeetingTemplate], str]:
    template = _default_template()
    return {template.identifier: template}, template.identifier


def _default_template() -> MeetingTemplate:
    return MeetingTemplate(
        identifier=DEFAULT_TEMPLATE_ID,
        name="Meeting Minutes",
        content=_DEFAULT_TEMPLATE_TEXT,
    )


def _calculate_start_end(segments: Iterable[SpeakerSegment]) -> Tuple[float, float]:
    start, end = 0.0, 0.0
    first = True
    for segment in segments:
        if first:
            start = float(segment.start)
            end = float(segment.end)
            first = False
            continue
        start = min(start, float(segment.start))
        end = max(end, float(segment.end))
    if first:
        # No segments available, fallback to a one hour default slot.
        return 0.0, 3600.0
    if end <= start:
        end = start + 60.0
    return start, end


def _format_clock_time(seconds: float) -> str:
    total_seconds = max(0, int(seconds))
    hours, remainder = divmod(total_seconds, 3600)
    minutes, _ = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}"


def _safe_format(template: str, context: Mapping[str, str]) -> str:
    class _SafeDict(dict):
        def __missing__(self, key: str) -> str:  # type: ignore[override]
            return "{" + key + "}"

    safe_context: MutableMapping[str, str] = _SafeDict({k: str(v) for k, v in context.items()})
    return template.format_map(safe_context)


__all__ = [
    "MeetingTemplate",
    "DEFAULT_TEMPLATE_ID",
    "build_template_context",
    "get_meeting_template",
    "render_template_for_prompt",
]
