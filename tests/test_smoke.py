"""Smoke test (architecture section 11): every page loads in both languages, and every
interface string passed to t() has an English text."""

import ast
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from ra.ui.navigation import PLACEHOLDERS
from ra.ui.texts_en import EN

ROOT = Path(__file__).resolve().parents[1]
PAGES = ("oversikt", "om-appen", *(path for _, path, _, _ in PLACEHOLDERS))
UI_DIR = ROOT / "src" / "ra" / "ui"


def _run_page(path: str, lang: str) -> None:
    """One page as app.py draws it: theme, learner, navigation, then the page itself."""
    import streamlit as st

    from ra.services import learner
    from ra.ui.i18n import LANG_KEY
    from ra.ui.navigation import build_navigation, build_pages
    from ra.ui.theme import apply_theme

    st.session_state[LANG_KEY] = lang
    apply_theme()
    learner.get_or_create()
    build_navigation()
    build_pages()[path][2]()


@pytest.fixture(autouse=True)
def _local_database(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'smoke.db'}")
    monkeypatch.setenv("RA_SHOW_DRAFTS", "1")


@pytest.mark.parametrize("lang", ["sv", "en"])
@pytest.mark.parametrize("page", PAGES)
def test_every_page_loads(page: str, lang: str) -> None:
    at = AppTest.from_function(_run_page, args=(page, lang), default_timeout=120)
    at.run()
    assert not at.exception, (page, lang, [e.value for e in at.exception])


def _t_literals() -> set[str]:
    found: set[str] = set()
    for path in UI_DIR.rglob("*.py"):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            is_t = isinstance(node, ast.Call) and getattr(node.func, "id", None) == "t"
            if is_t and node.args and isinstance(node.args[0], ast.Constant):
                found.add(node.args[0].value)
    return found


def test_every_interface_string_has_english() -> None:
    missing = sorted(_t_literals() - set(EN))
    assert not missing, missing
