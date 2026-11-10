"""Placeholder page: group label, title and one sentence about the page."""

from ra.ui.i18n import t
from ra.ui.theme import page_title


def render(group: str, title: str, sentence: str) -> None:
    page_title(t(group), t(title), t(sentence))
