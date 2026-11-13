"""The shared verifikation component: konto, kontonamn, debet, kredit, totals, balance.

``voucher_grid`` is the editable grid (st.data_editor); the account column
offers every account as "1930 Företagskonto", so the learner can search by
number or by name. Amounts are typed as text and read by the service.
``voucher_table_html`` renders a verifikation read only. All text is escaped.
"""

from collections.abc import Sequence
from html import escape
from typing import Any

import streamlit as st

from ra.services import practice
from ra.services.views import AccountOption, RowInput, VoucherView
from ra.ui.i18n import t

EMPTY_ROWS = 4
COLUMNS = ("konto", "debet", "kredit")


def balance_html(view: VoucherView) -> str:
    """Balance indicator: colour, a sign and a sentence, so colour is never the only signal."""
    if not view.rows:
        text = t("Skriv in verifikationens rader. Summorna visas här.")
        return f'<div class="ra-balance">{escape(text)}</div>'
    if view.balanced:
        text = t("✓ Verifikationen balanserar. Summa debet {0}, summa kredit {1}.",
                 view.total_debet, view.total_kredit)
        return f'<div class="ra-balance ok">{escape(text)}</div>'
    text = t("✗ Verifikationen balanserar inte. Summa debet {0}, summa kredit {1}, "
             "differens {2}.", view.total_debet, view.total_kredit, view.difference)
    return f'<div class="ra-balance off">{escape(text)}</div>'


def voucher_table_html(view: VoucherView, with_balance: bool = False) -> str:
    """Read only verifikation as an HTML table built from escaped app data."""
    head = (f"<tr><th>{escape(t('Konto'))}</th><th>{escape(t('Kontonamn'))}</th>"
            f'<th class="ra-amount">{escape(t("Debet"))}</th>'
            f'<th class="ra-amount">{escape(t("Kredit"))}</th></tr>')
    body = "".join(
        f"<tr><td>{row.account}</td><td>{escape(row.name)}</td>"
        f'<td class="ra-amount">{escape(row.debet)}</td>'
        f'<td class="ra-amount">{escape(row.kredit)}</td></tr>'
        for row in view.rows
    )
    totals = (f'<tr class="ra-total"><td></td><td>{escape(t("Summa"))}</td>'
              f'<td class="ra-amount">{escape(view.total_debet)}</td>'
              f'<td class="ra-amount">{escape(view.total_kredit)}</td></tr>')
    table = f'<table class="ra-table">{head}{body}{totals}</table>'
    return table + (balance_html(view) if with_balance else "")


def voucher_table(view: VoucherView, with_balance: bool = False) -> None:
    st.html(voucher_table_html(view, with_balance))


def _text(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def voucher_grid(key: str, options: Sequence[AccountOption]) -> list[RowInput]:
    """Editable verifikation with running totals; returns the rows as typed."""
    initial = [{"konto": "", "debet": "", "kredit": ""} for _ in range(EMPTY_ROWS)]
    edited = st.data_editor(
        initial,
        key=key,
        num_rows="dynamic",
        hide_index=True,
        width="stretch",
        column_order=COLUMNS,
        column_config={
            "konto": st.column_config.SelectboxColumn(
                t("Konto och kontonamn"), options=[o.label for o in options], width="large",
                help=t("Skriv kontonummer eller kontonamn för att söka.")),
            "debet": st.column_config.TextColumn(
                t("Debet"), help=t("Belopp i kronor, till exempel 1 250,50."),
                alignment="right"),
            "kredit": st.column_config.TextColumn(
                t("Kredit"), help=t("Belopp i kronor, till exempel 1 250,50."),
                alignment="right"),
        },
    )
    rows = [RowInput(_text(r.get("konto")) or None, _text(r.get("debet")), _text(r.get("kredit")))
            for r in edited]
    st.html(balance_html(practice.totals(rows)))
    return rows
