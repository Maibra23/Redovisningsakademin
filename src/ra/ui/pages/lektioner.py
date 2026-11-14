"""Lektioner: the module list with progress, and one lesson in four steps.

Förklara (the four fields and the rules), Visa (worked example with
underlag, verifikation and the effect on the reports), Gör (exercises with
new numbers and tips) and Kontroll (a short check without tips). Layout and
widgets only; the content and the progress come from services.lessons.
"""

import uuid
from html import escape

import streamlit as st

from ra.services import learner, lessons, practice
from ra.services.lessons import LessonView, ModuleView
from ra.ui.components.document_viewer import document_viewer
from ra.ui.components.exercise import exercise_body, forget_hints, stored_result
from ra.ui.components.report_effect import effect_table
from ra.ui.components.voucher import voucher_table
from ra.ui.i18n import get_lang, t
from ra.ui.theme import info_box, page_title

SELECTED_KEY = "lektion_vald"
SLOT_PREFIX = "lektion_instans_"
RULE_PARAM = "regel"
FIELDS = (("vad", "Vad"), ("varfor", "Varför"), ("hur", "Hur"), ("nar", "När"))


def _paragraph(text: str) -> None:
    st.html(f'<p class="ra-lesson-text">{escape(text)}</p>')


def _open(lesson_id: str | None) -> None:
    if lesson_id is None:
        st.session_state.pop(SELECTED_KEY, None)
    else:
        st.session_state[SELECTED_KEY] = lesson_id


def _module(view: ModuleView) -> None:
    with st.container(border=True):
        st.subheader(f"{view.module_id.upper()} {view.title}", anchor=False)
        st.write(view.description)
        total = len(view.lessons)
        st.progress(view.done_count / total,
                    text=t("{0} av {1} lektioner klara", view.done_count, total))
        for summary in view.lessons:
            title_col, state_col, open_col = st.columns([6, 2, 2], vertical_alignment="center")
            title_col.write(summary.title)
            state_col.write(t("✓ Klar") if summary.done else t("Inte klar"))
            open_col.button(t("Öppna"), key=f"oppna_{summary.lesson_id}", width="stretch",
                            on_click=_open, args=(summary.lesson_id,))


def _overview(learner_id: uuid.UUID, lang: str) -> None:
    page_title(t("Lär"), t("Lektioner"),
               t("Varje lektion förklarar, visar ett exempel, låter dig öva och avslutas "
                 "med en kontroll."))
    modules = lessons.modules(learner_id, lang)
    if not modules:
        info_box(t("Det finns inga publicerade lektioner ännu."))
        return
    for view in modules:
        _module(view)


def _simplification(view: LessonView) -> None:
    if view.simplification:
        info_box(t("Förenklat exempel: {0}", view.simplification))


def _explain(view: LessonView, rules_page: st.Page) -> None:
    for field, label in FIELDS:
        st.subheader(t(label), anchor=False)
        _paragraph(getattr(view, field))
    _simplification(view)
    if view.rules:
        st.subheader(t("Regler"), anchor=False)
        for rule in view.rules:
            st.page_link(rules_page, label=f"{rule.reference}: {rule.title}",
                         icon=":material/gavel:", query_params={RULE_PARAM: rule.rule_id})


def _show(view: LessonView) -> None:
    example = view.example
    _paragraph(example.text)
    _simplification(view)
    document_viewer(example.document)
    st.subheader(t("Verifikation"), anchor=False)
    voucher_table(example.voucher, with_balance=True)
    st.subheader(t("Effekt på rapporterna"), anchor=False)
    income_col, balance_col = st.columns(2)
    with income_col:
        effect_table(t("Resultaträkning"), example.income_lines)
    with balance_col:
        effect_table(t("Tillgångar"), example.balance_assets,
                     (t("Summa tillgångar"), example.total_assets))
        effect_table(t("Eget kapital och skulder"), example.balance_equity_liabilities,
                     (t("Summa eget kapital och skulder"), example.total_equity_liabilities))


@st.fragment
def _slot(learner_id: uuid.UUID, lang: str, exercise_id: str, hints: bool, context: str) -> None:
    slot = SLOT_PREFIX + exercise_id
    view = practice.start_exercise(lang, exercise_id, st.session_state.get(slot))
    st.session_state[slot] = view.seed
    if exercise_body(learner_id, view, lang, hints=hints, context=context):
        st.session_state.pop(slot, None)
        forget_hints()
        st.rerun(scope="fragment")
    result = stored_result(view)
    if context == lessons.KONTROLL and result is not None and result.feedback.correct:
        st.success(t("Rätt på kontrollen."), icon=":material/check_circle:")


def _practise(learner_id: uuid.UUID, lang: str, view: LessonView) -> None:
    numbers = list(range(len(view.exercise_ids)))
    chosen = st.radio(t("Övning"), numbers, horizontal=True, key=f"gor_{view.lesson_id}",
                      format_func=lambda i: t("Övning {0}", i + 1))
    _slot(learner_id, lang, view.exercise_ids[chosen], True, practice.CONTEXT)


def _check(learner_id: uuid.UUID, lang: str, view: LessonView) -> None:
    info_box(t("Kontrollen har inga tips. Lektionen är klar när du har svarat rätt på "
               "varje fråga i kontrollen."))
    for number, exercise_id in enumerate(view.check_ids, start=1):
        if len(view.check_ids) > 1:
            st.subheader(t("Fråga {0}", number), anchor=False)
        _slot(learner_id, lang, exercise_id, False, lessons.KONTROLL)


def _lesson(learner_id: uuid.UUID, lang: str, lesson_id: str, rules_page: st.Page) -> None:
    try:
        view = lessons.lesson(learner_id, lang, lesson_id)
    except lessons.LessonError:
        _open(None)
        st.rerun()
    st.button(t("Till alla lektioner"), icon=":material/arrow_back:", on_click=_open,
              args=(None,))
    page_title(f"{view.module_id.upper()} {view.module_title}", view.title)
    st.caption(t("Materialet är till för utbildning och är inte juridisk eller skattemässig "
                 "rådgivning."))
    if view.done:
        st.success(t("Du har klarat kontrollen i den här lektionen."),
                   icon=":material/check_circle:")
    explain, show, practise, check = st.tabs(
        [t("1 Förklara"), t("2 Visa"), t("3 Gör"), t("4 Kontroll")])
    with explain:
        _explain(view, rules_page)
    with show:
        _show(view)
    with practise:
        _practise(learner_id, lang, view)
    with check:
        _check(learner_id, lang, view)


def render(rules_page: st.Page) -> None:
    lang = get_lang()
    learner_id = learner.get_or_create()
    selected = st.session_state.get(SELECTED_KEY)
    if selected:
        _lesson(learner_id, lang, selected, rules_page)
    else:
        _overview(learner_id, lang)
