"""Hint button: shows the exercise's tip and remembers that a hint was used."""

import streamlit as st

from ra.ui.i18n import t
from ra.ui.theme import info_box


def hint_button(key: str, hint: str) -> int:
    """Number of hints used for this exercise instance (0 or 1)."""
    state_key = f"{key}_visad"
    if not st.session_state.get(state_key) and st.button(t("Visa tips"), key=key):
        st.session_state[state_key] = True
    if st.session_state.get(state_key):
        info_box(hint)
        return 1
    return 0
