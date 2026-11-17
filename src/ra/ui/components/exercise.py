"""One exercise instance: instruction, underlag, answer widget, tip, buttons and feedback.

Shared by Övningar, the Gör and Kontroll steps of a lesson, and Repetition.
Layout and widgets only; grading happens in services.practice. The result
of the latest answer is kept in session state under the instance key
(exercise id and seed), so a rerun shows the same feedback.
"""

import uuid
from collections.abc import Callable

import streamlit as st

from ra.services import practice
from ra.services.views import AvstamningInput, ExerciseView, InputProblem, SubmitResult
from ra.ui.components.document_viewer import document_viewer
from ra.ui.components.feedback_panel import feedback_panel
from ra.ui.components.hint import hint_button
from ra.ui.components.statement import statement_marker, statement_table
from ra.ui.components.tutor import state_key, tutor_controls
from ra.ui.components.voucher import voucher_grid, voucher_table
from ra.ui.i18n import t

RESULT_PREFIX = "resultat_"
STORY_LABEL = ("Sammanhanget i underlaget är skrivet av AI. Belopp och konton kommer från "
               "appens bokföringsmotor.")
HINT_PREFIX = "tips_"
HINT_USED_SUFFIX = "_visad"  # the suffix hint_button adds to its key

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


def instance_key(view: ExerciseView) -> str:
    return _key(view.exercise_id, view.seed)


def _key(exercise_id: str, seed: int) -> str:
    return f"{exercise_id}_{seed}"


def forget_instance(exercise_id: str, seed: int) -> None:
    """Drop the tip state and the result of one instance when a new one replaces it.

    Only that instance is cleared, so a tip shown in another open exercise still counts.
    """
    key = _key(exercise_id, seed)
    st.session_state.pop(f"{HINT_PREFIX}{key}{HINT_USED_SUFFIX}", None)
    st.session_state.pop(RESULT_PREFIX + key, None)
    st.session_state.pop(state_key(key), None)
    practice.forget_story(exercise_id, seed)


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
    return st.radio(t("Alternativ"), range(len(view.options)), index=None,
                    format_func=lambda i: view.options[i], key=f"val_{key}")


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


def show_result(result: SubmitResult, view: ExerciseView | None = None, lang: str = "sv",
                ai: bool = True) -> None:
    for problem in result.problems:
        st.warning(t(PROBLEM_TEXTS[problem]), icon=":material/edit:")
    if result.feedback is None:
        return
    feedback_panel(result.feedback)
    if result.attempt_no > 1:
        st.caption(t("Försök {0} på samma uppgift ger ingen XP och räknas inte för din nivå.",
                     result.attempt_no))
    elif result.xp_capped and result.feedback.correct:
        st.caption(t("Du fick {0} XP. Totalt har du {1} XP. Fler rätt på samma övning i dag ger "
                     "mindre eller ingen XP.", result.xp, result.total_xp))
    else:
        st.caption(t("Du fick {0} XP. Totalt har du {1} XP.", result.xp, result.total_xp))
    if ai and view is not None:
        tutor_controls(instance_key(view), view.exercise_id, view.seed, result, lang)


def stored_result(view: ExerciseView) -> SubmitResult | None:
    """The graded result for this instance, if the learner has answered it."""
    stored = st.session_state.get(RESULT_PREFIX + instance_key(view))
    return stored if stored is not None and stored.feedback is not None else None


def exercise_question(view: ExerciseView) -> object:
    """Instruction, underlag and answer widget; returns the answer as typed so far.

    Also used alone by Prov, where there are no tips, buttons or feedback per item.
    """
    st.write(view.instruction or t(DEFAULT_INSTRUCTIONS[view.typ]))
    if view.document:
        document_viewer(view.document)
        if view.story_by_ai:
            st.caption(t(STORY_LABEL))
    return ANSWER_WIDGETS[view.typ](view, instance_key(view))


def exercise_body(learner_id: uuid.UUID, view: ExerciseView, lang: str, *, hints: bool = True,
                  context: str = practice.CONTEXT,
                  on_new: Callable[[], None] | None = None,
                  on_scenario: Callable[[], None] | None = None) -> None:
    """Draw one exercise instance.

    ``on_new`` runs as the click callback of "Ny uppgift", before the rerun, so the
    next run draws the new instance; without it the button is hidden, for flows that
    move on themselves. ``on_scenario`` likewise runs for "Nytt scenario", which is
    shown only when it is given.
    """
    key = instance_key(view)
    result_key = RESULT_PREFIX + key
    answer = exercise_question(view)
    used_hints = hint_button(f"{HINT_PREFIX}{key}", view.hint) if hints else 0
    answered = stored_result(view) is not None
    submit, new, *scenario = st.columns(3 if on_scenario else 2)
    submit_label = t("Rätta igen (räknas inte)") if answered else t("Rätta svaret")
    if submit.button(submit_label, type="secondary" if answered else "primary",
                     key=f"ratta_{key}", width="stretch"):
        st.session_state[result_key] = practice.submit(
            learner_id, view.exercise_id, view.seed, answer, used_hints, lang, context)
    if on_new is not None:
        new.button(t("Ny uppgift"), type="primary" if answered else "secondary",
                   key=f"ny_{key}", width="stretch", on_click=on_new)
    if on_scenario is not None:
        scenario[0].button(t("Nytt scenario"), key=f"scenario_{key}", width="stretch",
                           icon=":material/auto_awesome:", on_click=on_scenario)
    stored = st.session_state.get(result_key)
    if stored is not None:
        show_result(stored, view, lang)
