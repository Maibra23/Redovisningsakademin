"""Grouped navigation (PRD section 11) and the sidebar links below it.

Page titles and group headers are translated on every run, so the menu
follows the language switch. URL paths are fixed ASCII and do not change
with the language.
"""

from functools import partial

import streamlit as st

from ra.ui.i18n import t
from ra.ui.pages import om_appen, oversikt, placeholder

LEARN = "Lär"
PRACTICE = "Praktik"
PROGRESS = "Min utveckling"

# (group, url path, title, one sentence about the page)
PLACEHOLDERS: tuple[tuple[str, str, str, str], ...] = (
    (LEARN, "lektioner", "Lektioner",
     "Lektionerna förklarar varje moment med ett genomräknat exempel."),
    (LEARN, "ovningar", "Övningar",
     "Övningarna ger dig nya siffror varje gång och återkoppling på varje svar."),
    (LEARN, "repetition", "Repetition",
     "Repetitionen tar tillbaka det du har övat efter en, tre och sju dagar."),
    (LEARN, "prov", "Prov",
     "Proven visar vad du kan utan ledtrådar."),
    (PRACTICE, "simulator", "Bokföringssimulatorn",
     "I simulatorn bokför du en hel månad för ett fiktivt aktiebolag."),
    (PRACTICE, "regelbibliotek", "Regelbibliotek",
     "Regelbiblioteket samlar reglerna som övningarna hänvisar till, med källa."),
    (PRACTICE, "kontoplan", "Kontoplan",
     "Kontoplanen visar de konton i BAS-kontoplanen som appen använder."),
    (PROGRESS, "kompetensprofil", "Kompetensprofil",
     "Kompetensprofilen visar hur säker du är på varje färdighet."),
    (PROGRESS, "prestationer", "Prestationer",
     "Här ser du dina prestationer och din XP."),
    (PROGRESS, "installningar", "Inställningar",
     "Här hittar du din sparkod och kan återställa eller radera din progression."),
)


def _placeholder_page(group: str, path: str, title: str, sentence: str) -> st.Page:
    return st.Page(
        partial(placeholder.render, group, title, sentence), title=t(title), url_path=path
    )


def build_navigation() -> st.Page:
    """Register all pages, draw the sidebar menu and return the selected page."""
    groups: dict[str, list[st.Page]] = {LEARN: [], PRACTICE: [], PROGRESS: []}
    for group, path, title, sentence in PLACEHOLDERS:
        groups[group].append(_placeholder_page(group, path, title, sentence))
    lessons, exercises = groups[LEARN][0], groups[LEARN][1]
    home = st.Page(
        partial(oversikt.render, lessons, exercises),
        title=t("Översikt"),
        url_path="oversikt",
        default=True,
    )
    about = st.Page(
        om_appen.render, title=t("Om appen och integritet"), url_path="om-appen",
        visibility="hidden",
    )
    sections = {t("Hem"): [home, about]} | {t(name): pages for name, pages in groups.items()}
    selected = st.navigation(sections, expanded=True)
    with st.sidebar:
        st.page_link(about, label=t("Om appen och integritet"))
        st.link_button(t("Rapportera fel"), om_appen.ISSUES_URL)
    return selected
