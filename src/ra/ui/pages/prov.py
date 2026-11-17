"""Prov: the list of exams, an exam in progress and the result.

Layout and widgets only; drawing, grading and storing are in services.exams.
During an exam there are no tips, no AI controls and no feedback; the page
keeps only the exam id and its seed. After submission the result is kept in
session state until the learner goes back to the list.
"""

import streamlit as st

from ra.services import exams, learner
from ra.services.views import ExamResultView, ExamSummaryView, ExamView
from ra.ui.components.exercise import PROBLEM_TEXTS, exercise_question
from ra.ui.components.feedback_panel import feedback_panel
from ra.ui.i18n import get_lang, t
from ra.ui.theme import info_box, kpi_tile, page_title

ACTIVE_KEY = "prov_aktivt"
RESULT_KEY = "prov_resultat"


def _start(exam_id: str, lang: str) -> None:
    view = exams.start(lang, exam_id)
    st.session_state[ACTIVE_KEY] = {"exam_id": view.exam_id, "seed": view.seed}


def _leave() -> None:
    st.session_state.pop(ACTIVE_KEY, None)
    st.session_state.pop(RESULT_KEY, None)


def _summary(view: ExamSummaryView, lang: str) -> None:
    with st.container(border=True):
        text, action = st.columns([3, 1], vertical_alignment="center")
        with text:
            st.subheader(view.title, anchor=False)
            st.write(t("{0} uppgifter. Godkänt från {1} %.", view.items, view.pass_percent))
            if view.best_correct is None:
                st.caption(t("Inte gjort ännu."))
            else:
                best = t("{0} av {1} rätt ({2} %)", view.best_correct, view.items,
                         view.best_percent)
                status = t("Godkänt") if view.passed else t("Inte godkänt ännu")
                st.caption(t("Bästa resultat {0}. {1}. Antal försök: {2}.", best, status,
                             view.attempts))
        action.button(t("Starta provet"), key=f"starta_{view.exam_id}", width="stretch",
                      type="primary", on_click=_start, args=(view.exam_id, lang))


def _exam(view: ExamView, lang: str) -> None:
    learner_id = learner.get_or_create()
    st.subheader(view.title, anchor=False)
    info_box(t("Under provet finns inga tips, ingen AI-hjälp och ingen återkoppling. Du ser "
               "resultatet när du lämnar in. Godkänt från {0} %.", view.pass_percent))
    answers = []
    for number, item in enumerate(view.items, start=1):
        with st.container(border=True):
            st.markdown(f"**{t('Uppgift {0} av {1}', number, len(view.items))}**")
            answers.append(exercise_question(item))
    submit, cancel = st.columns(2)
    if submit.button(t("Lämna in provet"), type="primary", width="stretch"):
        st.session_state[RESULT_KEY] = exams.submit(learner_id, lang, view.exam_id, view.seed,
                                                    answers)
        st.session_state.pop(ACTIVE_KEY, None)
        st.rerun()
    cancel.button(t("Avbryt provet"), width="stretch", on_click=_leave)


def _result(result: ExamResultView) -> None:
    st.subheader(result.title, anchor=False)
    score, verdict = st.columns(2)
    with score:
        kpi_tile(t("Resultat"), t("{0} av {1} rätt ({2} %)", result.correct, result.total,
                                  result.percent))
    with verdict:
        kpi_tile(t("Godkänt från {0} %", result.pass_percent),
                 t("✓ Godkänt") if result.passed else t("✗ Inte godkänt"),
                 "success" if result.passed else "danger")
    if result.badge:
        st.success(t("Märke: {0}. Du har klarat slutprovet.", result.badge),
                   icon=":material/workspace_premium:")
    st.caption(t("Provet är godkänt och räknas in i din nivå för varje färdighet.")
               if result.passed else
               t("Resultatet är sparat. Ett prov räknas in i din nivå först när det är godkänt."))
    for item in result.items:
        st.markdown(f"**{t('Uppgift {0}', item.number)}**")
        for problem in item.problems:
            st.warning(t(PROBLEM_TEXTS[problem]), icon=":material/edit:")
        feedback_panel(item.feedback)
    st.button(t("Tillbaka till proven"), type="primary", on_click=_leave)


def render() -> None:
    lang = get_lang()
    learner_id = learner.get_or_create()
    page_title(t("Lär"), t("Prov"),
               t("Proven visar vad du kan utan ledtrådar. Varje prov har nya siffror."))
    result = st.session_state.get(RESULT_KEY)
    if result is not None:
        _result(result)
        return
    active = st.session_state.get(ACTIVE_KEY)
    if active is not None:
        _exam(exams.exam_view(lang, active["exam_id"], active["seed"]), lang)
        return
    summaries = exams.exam_list(learner_id, lang)
    if not summaries:
        info_box(t("Det finns inga publicerade prov ännu."))
        return
    for view in summaries:
        _summary(view, lang)
