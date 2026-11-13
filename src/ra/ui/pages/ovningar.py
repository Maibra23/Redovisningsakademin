"""Övningar: choose a skill and a difficulty, do an exercise, get feedback.

Layout and widgets only; every decision is made in services.practice. The
current exercise instance (exercise id and seed) lives in session state, so
a rerun shows the same numbers until the learner asks for a new exercise.
"""

import uuid
from collections.abc import Callable

import streamlit as st

from ra.services import learner, practice
from ra.services.views import (
    AvstamningInput,
    ExerciseView,
    InputProblem,
    SkillView,
    SubmitResult,
)
from ra.ui.components.document_viewer import document_viewer
from ra.ui.components.feedback_panel import feedback_panel
from ra.ui.components.hint import hint_button
from ra.ui.components.statement import statement_marker, statement_table
from ra.ui.components.voucher import voucher_grid, voucher_table
from ra.ui.i18n import get_lang, t
from ra.ui.theme import info_box, kpi_tile, page_title

CURRENT_KEY = "ovning_aktuell"
RESULT_KEY = "ovning_resultat"

DIFFICULTY_NAMES = {"grund": "Grund", "medel": "Medel", "avancerad": "Avancerad"}
STATE_NAMES = {"ej_paborjad": "Ej påbörjad", "ovar": "Övar", "kompetent": "Kompetent",
               "befast": "Befäst"}
STATE_VARIANTS = {"ej_paborjad": "default", "ovar": "warning", "kompetent": "success",
                  "befast": "success"}
PROBLEM_TEXTS = {
    InputProblem.BELOPP_OLASLIGT:
        "Ett belopp kunde inte läsas. Skriv beloppet med siffror, till exempel 1 250,50.",
    InputProblem.KONTO_SAKNAS:
        "En rad har ett belopp men inget konto. Välj ett konto för varje rad med belopp.",
    InputProblem.BADA_SIDOR:
        "En rad har belopp i både debet och kredit. Skriv varje belopp på en egen rad.",
    InputProblem.TOMT_SVAR: "Du har inte skrivit något svar ännu.",
}
DEFAULT_INSTRUCTIONS = {
    "kontering": "Bokför underlaget.",
    "berakning": "Beräkna beloppet som saknas.",
    "klassificering": "Placera varje post i rätt grupp.",
    "resonemang": "Välj det bästa svaret.",
    "hitta_felet": "Verifikationen nedan innehåller ett fel. Bokför en rättelseverifikation.",
    "avstamning": ("Jämför kontoutdraget med bankkontot i huvudboken. Markera raderna som "
                   "skiljer sig och bokför det som behövs för att saldona ska stämma."),
}


def _instance_key(view: ExerciseView) -> str:
    return f"{view.exercise_id}_{view.seed}"


def _new_exercise(learner_id: uuid.UUID, skill_id: str, difficulty: str, lang: str) -> None:
    view = practice.next_exercise(learner_id, skill_id, difficulty, lang)
    st.session_state[CURRENT_KEY] = (
        {"skill": skill_id, "difficulty": difficulty, "exercise_id": view.exercise_id,
         "seed": view.seed} if view else None)
    st.session_state.pop(RESULT_KEY, None)


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


def _answer_kontering(view: ExerciseView, key: str) -> object:
    return voucher_grid(f"grid_{key}", practice.account_options())


def _answer_berakning(view: ExerciseView, key: str) -> object:
    return st.text_input(t("Ditt svar i kronor"), key=f"belopp_{key}",
                         placeholder=t("Till exempel 1 250,50"))


def _answer_klassificering(view: ExerciseView, key: str) -> object:
    return {item: st.selectbox(item, view.categories, index=None, key=f"klass_{key}_{i}",
                               placeholder=t("Välj grupp"))
            for i, item in enumerate(view.items)}


def _answer_resonemang(view: ExerciseView, key: str) -> object:
    st.write(view.question)
    chosen = st.radio(t("Alternativ"), range(len(view.options)), index=None,
                      format_func=lambda i: view.options[i], key=f"val_{key}")
    return chosen


def _answer_hitta_felet(view: ExerciseView, key: str) -> object:
    st.subheader(t("Bokförd verifikation"), anchor=False)
    if view.booked:
        voucher_table(view.booked)
    st.subheader(t("Din rättelseverifikation"), anchor=False)
    return voucher_grid(f"grid_{key}", practice.account_options())


def _answer_avstamning(view: ExerciseView, key: str) -> object:
    st.subheader(t("Kontoutdrag"), anchor=False)
    marked = statement_marker(f"utdrag_{key}", view.statement)
    st.subheader(t("Bankkontot i huvudboken"), anchor=False)
    statement_table(view.ledger)
    st.subheader(t("Dina verifikationer"), anchor=False)
    rows = voucher_grid(f"grid_{key}", practice.account_options())
    return AvstamningInput(marked, tuple(rows))


ANSWER_WIDGETS: dict[str, Callable[[ExerciseView, str], object]] = {
    "kontering": _answer_kontering,
    "berakning": _answer_berakning,
    "klassificering": _answer_klassificering,
    "resonemang": _answer_resonemang,
    "hitta_felet": _answer_hitta_felet,
    "avstamning": _answer_avstamning,
}


def _show_result(result: SubmitResult) -> None:
    for problem in result.problems:
        st.warning(t(PROBLEM_TEXTS[problem]), icon=":material/edit:")
    if result.feedback is None:
        return
    feedback_panel(result.feedback)
    if result.attempt_no > 1:
        st.caption(t("Försök {0} på samma uppgift ger ingen XP och räknas inte för din nivå.",
                     result.attempt_no))
    else:
        st.caption(t("Du fick {0} XP. Totalt har du {1} XP.", result.xp, result.total_xp))


@st.fragment
def _exercise(learner_id: uuid.UUID, skill_id: str, difficulty: str, lang: str) -> None:
    view = _current(learner_id, skill_id, difficulty, lang)
    tiles = st.container()
    if view is None:
        info_box(t("Det finns ingen övning på den här nivån ännu."))
        return
    key = _instance_key(view)
    st.write(view.instruction or t(DEFAULT_INSTRUCTIONS[view.typ]))
    if view.document:
        document_viewer(view.document)
    answer = ANSWER_WIDGETS[view.typ](view, key)
    hints = hint_button(f"tips_{key}", view.hint)
    submit, new = st.columns(2)
    if submit.button(t("Rätta svaret"), type="primary", key=f"ratta_{key}",
                     width="stretch"):
        st.session_state[RESULT_KEY] = (key, practice.submit(
            learner_id, view.exercise_id, view.seed, answer, hints, lang))
    if new.button(t("Ny uppgift"), key=f"ny_{key}", width="stretch"):
        _new_exercise(learner_id, skill_id, difficulty, lang)
        st.rerun(scope="fragment")
    stored = st.session_state.get(RESULT_KEY)
    if stored and stored[0] == key:
        _show_result(stored[1])
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
