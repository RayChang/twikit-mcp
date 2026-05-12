"""Pytest configuration for tweety_mcp tests.

This project uses a ``src`` layout. Insert ``src`` on ``sys.path`` during
tests so imports work in a clean checkout without requiring an editable
install as a precondition.
"""

from pathlib import Path
import sys


SRC = Path(__file__).resolve().parents[1] / "src"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
