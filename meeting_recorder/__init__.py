"""Top level package for the Meeting Recorder application."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover - imported only for type checking
    import gradio as gr


def build_app() -> "gr.Blocks":
    """Return the configured Gradio application."""

    from .app import build_app as _build_app

    return _build_app()


__all__ = ["build_app"]
