"""How one verifikation changes the resultaträkning and the balansräkning.

A read only table per report: the lines that change and the signed change,
right aligned in the tabular font. All text is escaped.
"""

from collections.abc import Sequence
from html import escape

import streamlit as st

from ra.services.lessons import EffectLine
from ra.ui.i18n import t


def _rows(lines: Sequence[EffectLine]) -> str:
    return "".join(f'<tr><td>{escape(line.label)}</td>'
                   f'<td class="ra-amount">{escape(line.amount)}</td></tr>' for line in lines)


def effect_table(title: str, lines: Sequence[EffectLine], total: tuple[str, str] | None = None
                 ) -> None:
    head = (f"<tr><th>{escape(title)}</th>"
            f'<th class="ra-amount">{escape(t("Förändring"))}</th></tr>')
    body = _rows(lines) if lines else (
        f'<tr><td colspan="2">{escape(t("Ingen förändring"))}</td></tr>')
    foot = (f'<tr class="ra-total"><td>{escape(total[0])}</td>'
            f'<td class="ra-amount">{escape(total[1])}</td></tr>' if total else "")
    st.html(f'<table class="ra-table">{head}{body}{foot}</table>')
