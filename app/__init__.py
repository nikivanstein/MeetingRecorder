"""Meeting recorder application package."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover - imported for type checkers only
    from flask import Flask


def create_app() -> "Flask":
    """Factory that defers importing Flask until needed."""

    from .main import create_app as _create_app

    return _create_app()


__all__ = ["create_app"]
