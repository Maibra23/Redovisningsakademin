"""Runs scripts/validate_content.py on content/ (architecture section 11)."""

import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "validate_content.py"


def test_content_is_valid() -> None:
    run = subprocess.run([sys.executable, str(SCRIPT)], capture_output=True, text=True)
    assert run.returncode == 0, run.stdout + run.stderr
