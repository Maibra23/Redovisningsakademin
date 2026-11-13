"""Where the content folder and the local database live.

The app is run from the repository root (``streamlit run app.py``), and CI
installs the package into site-packages, so paths are taken from the
environment or the working directory first and from the package location
only as a last resort.
"""

import os
from pathlib import Path

CONTENT_ROOT_ENV = "RA_CONTENT_ROOT"
PACKAGE_REPO_ROOT = Path(__file__).resolve().parents[2]


def repo_root() -> Path:
    """The working directory when it holds the content folder, else the package's repository."""
    cwd = Path.cwd()
    return cwd if (cwd / "content").is_dir() else PACKAGE_REPO_ROOT


def content_root() -> Path:
    """``RA_CONTENT_ROOT`` when set, else ``<repo root>/content``."""
    override = os.environ.get(CONTENT_ROOT_ENV)
    return Path(override) if override else repo_root() / "content"
