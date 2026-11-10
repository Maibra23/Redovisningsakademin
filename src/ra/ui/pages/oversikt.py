"""Start view: welcome and the two ways in, for new and experienced learners."""

import streamlit as st

from ra.ui.i18n import t
from ra.ui.theme import page_title


def _choice(title: str, text: str, target: st.Page, link_label: str) -> None:
    with st.container(border=True):
        st.subheader(t(title), anchor=False)
        st.write(t(text))
        st.page_link(target, label=t(link_label), icon=":material/arrow_forward:")


def render(lessons: st.Page, exercises: st.Page) -> None:
    page_title(
        t("Hem"),
        t("Välkommen till Redovisningsakademin"),
        t(
            "Öva svensk bokföring med BAS-kontoplanen och få veta exakt vad som blev fel "
            "och varför."
        ),
    )
    new_col, experienced_col = st.columns(2)
    with new_col:
        _choice(
            "Jag är ny",
            "Börja med grunderna. Lektionerna förklarar varje moment med ett exempel.",
            lessons,
            "Till lektionerna",
        )
    with experienced_col:
        _choice(
            "Jag har erfarenhet",
            "Gå direkt till övningarna och träna det du behöver.",
            exercises,
            "Till övningarna",
        )
