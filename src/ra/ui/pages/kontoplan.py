"""Kontoplan: the accounts the app uses, grouped by kontoklass, with search and a clear
credit to BAS as the source of the kontoplan.

Layout and widgets only; the accounts come from services.reference.
"""

from html import escape

import streamlit as st

from ra.services import reference
from ra.services.reference import AccountClassView
from ra.ui.i18n import get_lang, t
from ra.ui.theme import info_box, page_title

BAS_URL = "https://www.bas.se/kontoplaner/"
CLASS_NAMES = {
    1: "Tillgångar",
    2: "Eget kapital och skulder",
    3: "Rörelsens inkomster",
    4: "Kostnader för varor och material",
    5: "Övriga externa kostnader",
    6: "Övriga externa kostnader",
    7: "Kostnader för personal och avskrivningar",
    8: "Finansiella poster och skatt",
}
KIND_NAMES = {"tillgang": "Tillgång", "eget_kapital": "Eget kapital", "skuld": "Skuld",
              "intakt": "Intäkt", "kostnad": "Kostnad"}
SIDE_NAMES = {"debet": "Debet", "kredit": "Kredit"}


def _credit() -> None:
    source = reference.chart_source()
    text = t("Kontonummer och kontonamn kommer från {0}, utgiven av BAS. Upphovsrätten till "
             "kontoplanen tillhör BAS. Appen visar bara de konton som lektionerna och "
             "övningarna använder. Kontrollerad mot källan {1}.",
             source.publication, source.checked_on)
    link = (f'<a href="{escape(BAS_URL, quote=True)}" target="_blank" '
            f'rel="noopener noreferrer">{escape(t("BAS-kontoplanen hos BAS"))}</a>')
    st.html(f'<div class="ra-info">{escape(text)} {link}</div>')


def _class_table(group: AccountClassView) -> None:
    head = (f"<tr><th>{escape(t('Konto'))}</th><th>{escape(t('Kontonamn'))}</th>"
            f"<th>{escape(t('Typ'))}</th><th>{escape(t('Ökar i'))}</th></tr>")
    body = "".join(
        f'<tr><td class="ra-amount">{a.number}</td><td>{escape(a.name)}</td>'
        f"<td>{escape(t(KIND_NAMES[a.kind]))}</td>"
        f"<td>{escape(t(SIDE_NAMES[a.normal_side]))}</td></tr>"
        for a in group.accounts)
    st.html(f'<table class="ra-table">{head}{body}</table>')


def render() -> None:
    get_lang()
    page_title(t("Praktik"), t("Kontoplan"),
               t("Kontona i BAS-kontoplanen som appen använder, ordnade efter kontoklass."))
    _credit()
    query = st.text_input(
        t("Sök konto"), key="konto_sok",
        placeholder=t("Kontonummer eller kontonamn, till exempel 1930 eller moms"))
    groups = reference.accounts(query)
    if not groups:
        info_box(t("Inget konto matchar sökningen."))
    for group in groups:
        st.subheader(t("Kontoklass {0}: {1}", group.account_class,
                       t(CLASS_NAMES[group.account_class])), anchor=False)
        _class_table(group)
    st.caption(t("Typ och sidan där kontot ökar är appens egen indelning och ingår inte i "
                 "BAS publikation."))
