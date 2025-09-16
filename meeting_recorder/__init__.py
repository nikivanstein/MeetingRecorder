"""Meeting Recorder package."""

__all__ = ["create_app"]


def create_app():
    """Proxy import to avoid importing Gradio at module import time."""

    from .app import create_app as _create_app

    return _create_app()
