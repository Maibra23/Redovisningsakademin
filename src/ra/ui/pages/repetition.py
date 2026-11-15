"""Repetition: today's due skills as a short session of exercises with new numbers,
and a summary at the end.

The queue of skills, the position and the first result per skill live in
session state. Layout and widgets only; due skills, exercises and grading
come from services.practice.
"""

import uuid

import streamlit as st

from ra.services import learner, practice
from ra.services.views import SkillView
from ra.ui.components.exercise import exercise_body, forget_instance, stored_result
from ra.ui.i18n import get_lang, t
from ra.ui.theme import info_box, page_title

QUEUE_KEY = "rep_ko"
INDEX_KEY = "rep_position"
RESULTS_KEY = "rep_resultat"
CURRENT_KEY = "rep_aktuell"
CONTEXT = "repetition"
MAX_SKILLS = 10


def _start(skill_ids: list[str]) -> None:
    st.session_state[QUEUE_KEY] = skill_ids[:MAX_SKILLS]
    st.session_state[INDEX_KEY] = 0
    st.session_state[RESULTS_KEY] = {}
    st.session_state.pop(CURRENT_KEY, None)


def _forget_current() -> None:
    current = st.session_state.pop(CURRENT_KEY, None)
    if current is not None:
        forget_instance(*current)


def _finish() -> None:
    _forget_current()
    for key in (QUEUE_KEY, INDEX_KEY, RESULTS_KEY):
        st.session_state.pop(key, None)


def _next() -> None:
    _forget_current()
    st.session_state[INDEX_KEY] += 1


def _due_list(due: tuple[SkillView, ...]) -> None:
    session = due[:MAX_SKILLS]
    st.write(t("I dag är det dags att repetera {0} färdigheter.", len(due)))
    if len(due) > len(session):
        st.write(t("En repetition tar högst {0} färdigheter åt gången. De övriga finns kvar "
                   "nästa gång du öppnar sidan.", MAX_SKILLS))
    for skill in session:
        st.write(t("{0} {1}, planerad {2}", skill.skill_id, skill.name, skill.due_on))
    st.button(t("Starta repetitionen"), type="primary", on_click=_start,
              args=([s.skill_id for s in session],))


def _summary(learner_id: uuid.UUID, lang: str) -> None:
    results: dict[str, bool] = st.session_state[RESULTS_KEY]
    st.subheader(t("Sammanfattning"), anchor=False)
    st.write(t("Du svarade rätt på {0} av {1} uppgifter.", sum(results.values()), len(results)))
    for skill_id, correct in results.items():
        view = practice.skill_view(learner_id, skill_id, lang)
        mark = t("✓ Rätt") if correct else t("✗ Fel")
        next_due = view.due_on or t("Inte planerad")
        st.write(t("{0} {1} {2}. Nästa repetition: {3}.", mark, skill_id, view.name, next_due))
    st.button(t("Avsluta repetitionen"), type="primary", on_click=_finish)


@st.fragment
def _session(learner_id: uuid.UUID, lang: str) -> None:
    queue: list[str] = st.session_state[QUEUE_KEY]
    index: int = st.session_state[INDEX_KEY]
    if index >= len(queue):
        _summary(learner_id, lang)
        return
    skill_id = queue[index]
    st.progress(index / len(queue), text=t("Uppgift {0} av {1}", index + 1, len(queue)))
    current = st.session_state.get(CURRENT_KEY)
    if current is None:
        view = practice.next_exercise(learner_id, skill_id, None, lang)
        if view is None:
            _next()
            st.rerun()
        st.session_state[CURRENT_KEY] = (view.exercise_id, view.seed)
    else:
        view = practice.exercise_view(lang, *current)
    st.subheader(practice.skill_view(learner_id, skill_id, lang).name, anchor=False)
    exercise_body(learner_id, view, lang, context=CONTEXT)
    result = stored_result(view)
    if result is not None:
        st.session_state[RESULTS_KEY].setdefault(skill_id, result.feedback.correct)
        label = t("Nästa uppgift") if index + 1 < len(queue) else t("Visa sammanfattningen")
        st.button(label, type="primary", key=f"rep_nasta_{index}", on_click=_next)


def render() -> None:
    lang = get_lang()
    learner_id = learner.get_or_create()
    page_title(t("Lär"), t("Repetition"),
               t("Det du har övat kommer tillbaka efter en, tre och sju dagar, med nya siffror."))
    if QUEUE_KEY in st.session_state:
        _session(learner_id, lang)
        return
    due = practice.due_skills(learner_id, lang)
    if not due:
        info_box(t("Du har inget att repetera i dag. När du har övat på en färdighet kommer "
                   "den tillbaka här efter en dag."))
        return
    _due_list(due)
