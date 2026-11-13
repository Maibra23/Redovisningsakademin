"""Kontoutdrag and huvudbok lines for avstämning: a read only table and a marker."""

from collections.abc import Sequence
from html import escape

import streamlit as st

from ra.services.views import StatementLineView
from ra.ui.i18n import t


def statement_table(lines: Sequence[StatementLineView]) -> None:
    head = (f"<tr><th>{escape(t('Datum'))}</th><th>{escape(t('Text'))}</th>"
            f'<th class="ra-amount">{escape(t("Belopp"))}</th></tr>')
    body = "".join(f"<tr><td>{escape(ln.date)}</td><td>{escape(ln.text)}</td>"
                   f'<td class="ra-amount">{escape(ln.amount)}</td></tr>' for ln in lines)
    st.html(f'<table class="ra-table">{head}{body}</table>')


def statement_marker(key: str, lines: Sequence[StatementLineView]) -> frozenset[int]:
    """Kontoutdrag with a checkbox per line; returns the indexes of the marked lines."""
    edited = st.data_editor(
        [{"markera": False, "datum": ln.date, "text": ln.text, "belopp": ln.amount}
         for ln in lines],
        key=key,
        hide_index=True,
        width="stretch",
        disabled=("datum", "text", "belopp"),
        column_config={
            "markera": st.column_config.CheckboxColumn(t("Skiljer sig")),
            "datum": st.column_config.TextColumn(t("Datum")),
            "text": st.column_config.TextColumn(t("Text")),
            "belopp": st.column_config.TextColumn(t("Belopp"), alignment="right"),
        },
    )
    return frozenset(i for i, row in enumerate(edited) if row.get("markera") is True)
