"""Övningar: choose a skill and a difficulty, do an exercise, get feedback.

Layout and widgets only; every decision is made in services.practice. The
current exercise instance (exercise id and seed) lives in session state, so
a rerun shows the same numbers until the learner asks for a new exercise.
"""

import uuid

import streamlit as st

from ra.services import learner, practice
from ra.services.views import ExerciseView, SkillView
from ra.ui.components.exercise import exercise_body, forget_hints
from ra.ui.i18n import get_lang, t
from ra.ui.theme import info_box, kpi_tile, page_title

CURRENT_KEY = "ovning_aktuell"

DIFFICULTY_NAMES = {"grund": "Grund", "medel": "Medel", "avancerad": "Avancerad"}
STATE_NAMES = {"ej_paborjad": "Ej påbörjad", "ovar": "Övar", "kompetent": "Kompetent",
               "befast": "Befäst"}
STATE_VARIANTS = {"ej_paborjad": "default", "ovar": "warning", "kompetent": "success",
                  "befast": "success"}


def _new_exercise(learner_id: uuid.UUID, skill_id: str, difficulty: str, lang: str) -> None:
    view = practice.next_exercise(learner_id, skill_id, difficulty, lang)
    st.session_state[CURRENT_KEY] = (
        {"skill": skill_id, "difficulty": difficulty, "exercise_id": view.exercise_id,
         "seed": view.seed} if view else None)
    forget_hints()


def _current(learner_id: uuid.UUID, skill_id: str, difficulty: str,
             lang: str) -> ExerciseView | None:
    current = st.session_state.get(CURRENT_KEY)
    if not current or current["skill"] != skill_id or current["difficulty"] != difficulty:
        _new_exercise(learner_id, skill_id, difficulty, lang)
        current = st.session_state.get(CURRENT_KEY)
    if not current:
        return None
    return practice.exercise_view(lang, current["exercise_id"], current["seed"])


def _skill_tiles(view: SkillView) -> None:
    state, recent, due = st.columns(3)
    with state:
        kpi_tile(t("Din nivå"), t(STATE_NAMES[view.state.value]),
                 STATE_VARIANTS[view.state.value])
    with recent:
        share = (t("{0} % av {1} försök", view.recent_percent, view.total)
                 if view.recent_percent is not None else t("Inga försök ännu"))
        kpi_tile(t("Rätt bland de senaste"), share)
    with due:
        kpi_tile(t("Nästa repetition"), view.due_on or t("Inte planerad"))


@st.fragment
def _exercise(learner_id: uuid.UUID, skill_id: str, difficulty: str, lang: str) -> None:
    view = _current(learner_id, skill_id, difficulty, lang)
    tiles = st.container()
    if view is None:
        info_box(t("Det finns ingen övning på den här nivån ännu."))
        return
    if exercise_body(learner_id, view, lang):
        _new_exercise(learner_id, skill_id, difficulty, lang)
        st.rerun(scope="fragment")
    with tiles:
        _skill_tiles(practice.skill_view(learner_id, skill_id, lang))


def render() -> None:
    lang = get_lang()
    learner_id = learner.get_or_create()
    page_title(t("Lär"), t("Övningar"),
               t("Öva med nya siffror varje gång. Du får återkoppling på varje svar."))
    skills = {s.skill_id: s for s in practice.available_skills(lang)}
    if not skills:
        info_box(t("Det finns inga publicerade övningar ännu."))
        return
    skill_col, level_col = st.columns([2, 1])
    with skill_col:
        skill_id = st.selectbox(t("Område"), list(skills), key="ovning_kompetens",
                                format_func=lambda i: f"{i} {skills[i].name}")
    with level_col:
        difficulty = st.radio(t("Nivå"), skills[skill_id].difficulties, horizontal=True,
                              key=f"ovning_niva_{skill_id}",
                              format_func=lambda d: t(DIFFICULTY_NAMES[d]))
    _exercise(learner_id, skill_id, difficulty, lang)
