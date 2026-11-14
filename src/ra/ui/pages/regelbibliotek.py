"""Regelbibliotek: the rule entries with search, a filter by type of norm and each entry
in full, with its source link and the date it was last checked.

A lesson links to an entry with ?regel=<id>; that entry opens expanded.
Layout and widgets only; the entries come from services.reference.
"""

from html import escape

import streamlit as st

from ra.services import reference
from ra.services.reference import RuleView
from ra.ui.i18n import get_lang, t
from ra.ui.theme import info_box, page_title

RULE_PARAM = "regel"
NORM_NAMES = {
    "lag": "Lag",
    "förordning": "Förordning",
    "allmänt råd": "Allmänt råd",
    "vägledning": "Vägledning",
    "myndighetsinformation": "Myndighetsinformation",
}
NOTICE = ("Materialet är till för utbildning och är inte juridisk eller skattemässig "
          "rådgivning. Läs alltid den aktuella texten hos källan.")


def _field(label: str, text: str) -> str:
    return (f'<div class="ra-feedback-part"><div class="ra-feedback-label">{escape(label)}'
            f"</div><p>{escape(text)}</p></div>")


def _entry(rule: RuleView) -> None:
    link = (f'<a href="{escape(rule.source_url, quote=True)}" target="_blank" '
            f'rel="noopener noreferrer">{escape(t("Läs regeln hos källan"))}</a>')
    st.html(
        _field(t("Källa"), rule.name)
        + _field(t("Lagrum"), rule.section)
        + _field(t("Normtyp"), t(NORM_NAMES.get(rule.norm_type, rule.norm_type)))
        + _field(t("Förklaring"), rule.explanation)
        + _field(t("Exempel"), rule.example)
        + _field(t("I praktiken"), rule.in_practice)
        + f"<p>{link}</p>"
        + f'<p class="ra-muted">{escape(t("Senast kontrollerad: {0}", rule.checked_on))}</p>'
    )


def render() -> None:
    lang = get_lang()
    page_title(t("Praktik"), t("Regelbibliotek"),
               t("Reglerna som lektionerna och övningarna hänvisar till, med källa och datum "
                 "för den senaste kontrollen."))
    info_box(t(NOTICE))
    selected = st.query_params.get(RULE_PARAM)
    search_col, filter_col = st.columns([3, 2])
    with search_col:
        query = st.text_input(t("Sök"), key="regel_sok",
                              placeholder=t("Till exempel verifikation eller moms"))
    with filter_col:
        types = st.pills(t("Normtyp"), reference.norm_types(lang), selection_mode="multi",
                         key="regel_normtyp",
                         format_func=lambda n: t(NORM_NAMES.get(n, n)))
    found = reference.rules(lang, query, types or ())
    st.caption(t("{0} regler", len(found)))
    if not found:
        info_box(t("Ingen regel matchar sökningen."))
    for rule in found:
        with st.expander(f"{rule.reference}: {rule.title}", expanded=rule.rule_id == selected):
            _entry(rule)
