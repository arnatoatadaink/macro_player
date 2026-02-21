"""Shared test fixtures."""
import sys
from pathlib import Path

import pytest

# Ensure project root is on sys.path so `src.*` imports work
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
