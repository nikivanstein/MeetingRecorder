"""Test configuration for the Meeting Recorder package."""

import sys
from pathlib import Path

# Ensure the package root is importable when tests are executed from the tests directory.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
