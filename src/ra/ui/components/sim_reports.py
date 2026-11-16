"""The simulator's reports as tables: verifikationslista, huvudbok per konto, råbalans,
resultaträkning, balansräkning and momsrapport.

Every figure comes formatted from services.simulator, computed by core from the
learner's stored verifikationer. Amounts are right aligned in the tabular font.
Account names, report line names and the momsdeklaration fält stay in Swedish,
as in Swedish bookkeeping and on Skatteverket's form.
Verifikation texts were typed by the learner, so everything is escaped.
"""

from html import escape

import streamlit as st

from ra.services.views import (
    BalanceSheetView,
    IncomeStatementView,
    LedgerAccountView,
    ReportLineView,
    SimVoucherView,
    TrialBalanceView,
    VatReportView,
)
from ra.ui.i18n import t

VAT_FIELDS = {
    "10": "Utgående moms 25 %",
    "11": "Utgående moms 12 %",
    "12": "Utgående moms 6 %",
    "20": "Inköp av varor från ett annat EU-land",
    "21": "Inköp av tjänster från ett annat EU-land",
    "30": "Utgående moms 25 % på inköp från ett annat EU-land",
    "35": "Försäljning av varor till ett annat EU-land",
    "39": "Försäljning av tjänster till ett annat EU-land enligt huvudregeln",
    "48": "Ingående moms att dra av",
}


def _cell(text: str, amount: bool = False, css: str = "") -> str:
    classes = " ".join(c for c in ("ra-amount" if amount else "", css) if c)
    attribute = f' class="{classes}"' if classes else ""
    return f"<td{attribute}>{escape(text)}</td>"


def _head(*labels: str, amounts: int = 0) -> str:
    plain = len(labels) - amounts
    cells = "".join(f"<th>{escape(t(label))}</th>" for label in labels[:plain])
    cells += "".join(f'<th class="ra-amount">{escape(t(label))}</th>'
                     for label in labels[plain:])
    return f"<tr>{cells}</tr>"


def _table(rows: str) -> None:
    st.html(f'<table class="ra-table">{rows}</table>')


def _check(ok: bool, good: str, bad: str) -> None:
    """Indicator with colour, a sign and a sentence, so colour is never the only signal."""
    css, text = ("ok", f"✓ {good}") if ok else ("off", f"✗ {bad}")
    st.html(f'<div class="ra-balance {css}">{escape(text)}</div>')


def voucher_list(vouchers: tuple[SimVoucherView, ...]) -> None:
    """Verifikationslista: each verifikation with its rows and its rättelse links."""
    rows = _head("Ver", "Datum", "Konto", "Debet", "Kredit", amounts=2)
    for view in vouchers:
        links = []
        if view.corrects:
            links.append(t("Rättar verifikation {0}.", view.corrects))
        if view.corrected_by:
            links.append(t("Rättas av verifikation {0}.", ", ".join(view.corrected_by)))
        title = " ".join([view.text, *links])
        rows += (f'<tr class="ra-total">{_cell(view.label)}{_cell(view.date)}'
                 f'<td colspan="3">{escape(title)}</td></tr>')
        rows += "".join(
            f"<tr>{_cell('')}{_cell('')}{_cell(f'{r.account} {r.name}')}"
            f"{_cell(r.debet, True)}{_cell(r.kredit, True)}</tr>" for r in view.voucher.rows)
    _table(rows)


def ledger_account(account: LedgerAccountView) -> None:
    """Huvudbok for one konto: ingående balans, each entry, the movements and utgående balans."""
    rows = _head("Datum", "Ver", "Text", "Debet", "Kredit", amounts=2)
    rows += (f"<tr>{_cell('')}{_cell('')}{_cell(t('Ingående balans'))}"
             f'<td class="ra-amount" colspan="2">{escape(account.opening)}</td></tr>')
    rows += "".join(f"<tr>{_cell(e.date)}{_cell(e.label)}{_cell(e.text)}"
                    f"{_cell(e.debet, True)}{_cell(e.kredit, True)}</tr>"
                    for e in account.entries)
    rows += (f'<tr class="ra-total">{_cell("")}{_cell("")}{_cell(t("Summa rörelser"))}'
             f"{_cell(account.debet, True)}{_cell(account.kredit, True)}</tr>")
    rows += (f'<tr class="ra-total">{_cell("")}{_cell("")}{_cell(t("Utgående balans"))}'
             f'<td class="ra-amount" colspan="2">{escape(account.closing)}</td></tr>')
    _table(rows)
    st.caption(t("Balanser med minustecken är kreditsaldon."))


def trial_balance(view: TrialBalanceView) -> None:
    """Råbalans: every account's utgående balans in the debet or the kredit column."""
    rows = _head("Konto", "Kontonamn", "Debet", "Kredit", amounts=2)
    rows += "".join(f"<tr>{_cell(str(r.number))}{_cell(r.name)}{_cell(r.debet, True)}"
                    f"{_cell(r.kredit, True)}</tr>" for r in view.rows)
    rows += (f'<tr class="ra-total">{_cell("")}{_cell(t("Summa"))}'
             f"{_cell(view.total_debet, True)}{_cell(view.total_kredit, True)}</tr>")
    _table(rows)
    _check(view.balanced, t("Summa debet är lika med summa kredit."),
           t("Summa debet och summa kredit skiljer sig åt."))


def _lines(lines: tuple[ReportLineView, ...]) -> str:
    return "".join(f"<tr>{_cell(ln.label)}{_cell(ln.amount, True)}</tr>" for ln in lines)


def _subtotal(label: str, amount: str) -> str:
    return f'<tr class="ra-total">{_cell(label)}{_cell(amount, True)}</tr>'


def income_statement(view: IncomeStatementView) -> None:
    """Resultaträkning for the period, kostnadsslagsindelad."""
    rows = _head("Post", "Belopp", amounts=1)
    rows += _lines(view.operating) + _subtotal(t("Rörelseresultat"), view.operating_result)
    rows += _lines(view.financial) + _subtotal(t("Resultat efter finansiella poster"),
                                               view.result_after_financial)
    rows += _lines(view.tax) + _subtotal(t("Periodens resultat"), view.net_result)
    _table(rows)
    st.caption(t("Intäkter visas med plustecken och kostnader med minustecken."))


def balance_sheet(view: BalanceSheetView) -> None:
    """Balansräkning with the period's result in Årets resultat, before the bokslut."""
    rows = _head("Tillgångar", "Belopp", amounts=1)
    rows += _lines(view.assets) + _subtotal(t("Summa tillgångar"), view.total_assets)
    _table(rows)
    rows = _head("Eget kapital och skulder", "Belopp", amounts=1)
    rows += _lines(view.equity_and_liabilities) + _subtotal(
        t("Summa eget kapital och skulder"), view.total_equity_and_liabilities)
    _table(rows)
    _check(view.balanced, t("Balansräkningen balanserar: tillgångarna är lika stora som eget "
                            "kapital och skulder."),
           t("Balansräkningen balanserar inte."))
    st.caption(t("Periodens resultat ingår i Årets resultat, eftersom inget bokslut är gjort."))


def vat_report(view: VatReportView) -> None:
    """Momsrapport by momsdeklaration fält."""
    rows = _head("Fält", "Post", "Belopp", amounts=1)
    rows += "".join(f"<tr>{_cell(code)}{_cell(VAT_FIELDS[code])}{_cell(amount, True)}</tr>"
                    for code, amount in view.rows)
    net = t("Moms att betala") if view.to_pay else t("Moms att få tillbaka")
    rows += f'<tr class="ra-total">{_cell("49")}{_cell(net)}{_cell(view.net, True)}</tr>'
    _table(rows)
    st.caption(t("Momsrapporten gäller månadens verifikationer utom momsomföringen."))
