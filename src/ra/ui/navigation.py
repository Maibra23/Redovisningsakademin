"""Grouped navigation (PRD section 11) and the sidebar links below it.

Page titles and group headers are translated on every run, so the menu
follows the language switch. URL paths are fixed ASCII and do not change
with the language.
"""

from collections.abc import Callable
from functools import partial

import streamlit as st

from ra.ui.i18n import t
from ra.ui.pages import om_appen, oversikt, ovningar, placeholder

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


# Pages that are built; the rest still show their placeholder.
IMPLEMENTED = {"ovningar": ovningar.render}


Render = Callable[[], None]


def _render_for(path: str, group: str, title: str, sentence: str) -> Render:
    if path in IMPLEMENTED:
        return IMPLEMENTED[path]
    return partial(placeholder.render, group, title, sentence)


def build_pages() -> dict[str, tuple[str, st.Page, Render]]:
    """Every page by url path: its section, the st.Page and the function that draws it."""
    pages: dict[str, tuple[str, st.Page, Render]] = {}
    for group, path, title, sentence in PLACEHOLDERS:
        render = _render_for(path, group, title, sentence)
        pages[path] = (group, st.Page(render, title=t(title), url_path=path), render)
    lessons, exercises = pages["lektioner"][1], pages["ovningar"][1]
    home = partial(oversikt.render, lessons, exercises)
    pages["oversikt"] = ("Hem", st.Page(home, title=t("Översikt"), url_path="oversikt",
                                        default=True), home)
    pages["om-appen"] = ("Hem", st.Page(om_appen.render, title=t("Om appen och integritet"),
                                        url_path="om-appen", visibility="hidden"),
                         om_appen.render)
    return pages


def build_navigation() -> st.Page:
    """Register all pages, draw the sidebar menu and return the selected page."""
    pages = build_pages()
    sections: dict[str, list[st.Page]] = {t("Hem"): []}
    for name in (LEARN, PRACTICE, PROGRESS):
        sections[t(name)] = []
    for group, page, _ in pages.values():
        sections[t(group)].append(page)
    selected = st.navigation(sections, expanded=True)
    about = pages["om-appen"][1]
    with st.sidebar:
        st.page_link(about, label=t("Om appen och integritet"))
        st.link_button(t("Rapportera fel"), om_appen.ISSUES_URL)
    return selected
