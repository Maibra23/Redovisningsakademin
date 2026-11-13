"""Underlag as clean HTML: kundfaktura, leverantörsfaktura, kvitto, kontoutdrag and more.

Built only from app data and escaped. Document contents stay in Swedish in
both languages, as in Swedish bookkeeping; only the frame is translated.
"""

from html import escape

import streamlit as st

from ra.services.views import DocumentView
from ra.ui.i18n import t

KIND_NAMES: dict[str, str] = {
    "kundfaktura": "Kundfaktura",
    "kreditfaktura": "Kreditfaktura",
    "leverantorsfaktura": "Leverantörsfaktura",
    "kvitto": "Kvitto",
    "kontoutdrag": "Kontoutdrag",
    "lonespecifikation": "Lönespecifikation",
    "hyresavi": "Hyresavi",
    "internt_underlag": "Internt underlag",
}


def _amount_cell(amount: str | None) -> str:
    if amount is None:
        return f'<td class="ra-amount ra-hidden-amount">{escape(t("Att beräkna"))}</td>'
    return f'<td class="ra-amount">{escape(amount)}</td>'


def _rows(rows: tuple[tuple[str, str | None], ...], total: bool = False) -> str:
    css = ' class="ra-total"' if total else ""
    return "".join(f"<tr{css}><td>{escape(text)}</td>{_amount_cell(amount)}</tr>"
                   for text, amount in rows)


def document_viewer(view: DocumentView) -> None:
    kind = KIND_NAMES.get(view.kind, view.kind)
    text = f'<p class="ra-doc-text">{escape(view.text)}</p>' if view.text else ""
    st.html(
        f'<div class="ra-doc">'
        f'<div class="ra-doc-head"><div>'
        f'<div class="ra-doc-kind">{escape(t("Underlag"))}: {escape(kind)}</div>'
        f'<div class="ra-doc-title">{escape(view.title)}</div></div>'
        f'<div class="ra-doc-meta">{escape(view.counterparty)}<br>{escape(view.date)}</div>'
        f"</div>"
        f'<table class="ra-table">{_rows(view.rows)}{_rows(view.totals, total=True)}</table>'
        f"{text}</div>"
    )
