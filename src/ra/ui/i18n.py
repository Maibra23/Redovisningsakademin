"""Swedish and English interface language: t() and the language switch.

Swedish is the source language, and the Swedish text in the code is the
lookup key: ``t("Lektioner")`` returns the English text from
``ra.ui.texts_en.EN`` when the learner has chosen English, and the Swedish
text otherwise. A missing translation falls back to Swedish, so a new
string can never break a page.

Strings with values use numbered placeholders, so the template is the key
and the values are filled in afterwards: ``t("Du har {0} XP", xp)``.

The choice lives in ``st.session_state["lang"]`` and is mirrored to the
``lang`` query parameter, so it survives a reload and travels with a
shared link.
"""

from typing import Any

import streamlit as st

from ra.ui.texts_en import EN

LANG_KEY = "lang"
DEFAULT_LANG = "sv"
LANGUAGES: dict[str, str] = {"sv": "Svenska", "en": "English"}


def get_lang() -> str:
    """Current language code, "sv" (default) or "en"."""
    lang = st.session_state.get(LANG_KEY)
    if lang is None:
        lang = st.query_params.get(LANG_KEY, DEFAULT_LANG)
        if lang not in LANGUAGES:
            lang = DEFAULT_LANG
        st.session_state[LANG_KEY] = lang
    return lang if lang in LANGUAGES else DEFAULT_LANG


def translate(text: str, lang: str) -> str:
    """English text for ``text`` when ``lang`` is "en", else ``text``."""
    if lang == "en":
        return EN.get(text, text)
    return text


def t(text: str, *args: Any) -> str:
    """Translate ``text`` to the current language and fill in ``args``."""
    out = translate(text, get_lang())
    return out.format(*args) if args else out


def _sync_lang_param() -> None:
    """Mirror the language choice to the address (only English needs a parameter)."""
    if get_lang() == "en":
        if st.query_params.get(LANG_KEY) != "en":
            st.query_params[LANG_KEY] = "en"
    elif LANG_KEY in st.query_params:
        del st.query_params[LANG_KEY]


def render_language_switch() -> None:
    """Svenska / English switch in the sidebar.

    The widget key is the session key that get_lang() reads, so the whole
    page renders in the new language on the run after a click.
    """
    get_lang()
    with st.sidebar:
        st.radio(
            t("Språk"),
            options=list(LANGUAGES),
            format_func=LANGUAGES.__getitem__,
            key=LANG_KEY,
            horizontal=True,
        )
    _sync_lang_param()
