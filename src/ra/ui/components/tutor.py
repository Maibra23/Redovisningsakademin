"""AI controls under the feedback: Förklara med andra ord and Fråga handledaren.

Shown only when services.tutor is available. Model text and the learner's
question are escaped and labelled as AI; when the tutor has no text the page
words the reason and the built in feedback above stays the answer.
"""

from html import escape

import streamlit as st

from ra.services import tutor
from ra.services.views import SubmitResult, TutorReply, TutorStatus
from ra.ui.i18n import t

STATE_PREFIX = "handledare_"
AI_LABEL = "Förklaring skapad av AI. Facit och belopp kommer från appens bokföringsmotor."
MESSAGES = {
    TutorStatus.DECLINED: ("Handledaren svarar bara på frågor om den här uppgiften. Fråga gärna "
                           "om konteringen, beloppen eller regeln."),
    TutorStatus.NOT_AVAILABLE: ("Handledaren kunde inte ge ett säkert svar just nu. "
                                "Återkopplingen ovan gäller som vanligt."),
    TutorStatus.SESSION_FULL: ("Du har använt alla AI-förklaringar för den här sessionen. "
                               "Återkopplingen fungerar som vanligt."),
    TutorStatus.DAILY_FULL: ("Dagens AI-förklaringar är slut för hela appen och kommer tillbaka "
                             "i morgon. Återkopplingen fungerar som vanligt."),
}


def state_key(instance_key: str) -> str:
    return STATE_PREFIX + instance_key


def _show(reply: TutorReply) -> None:
    if reply.text is None:
        st.info(t(MESSAGES[reply.status]), icon=":material/info:")
        return
    paragraphs = "".join(f"<p>{escape(part)}</p>" for part in reply.text.split("\n") if part)
    st.html(f'<div class="ra-ai">{paragraphs}'
            f'<p class="ra-ai-label">{escape(t(AI_LABEL))}</p></div>')


def tutor_controls(instance_key: str, exercise_id: str, seed: int, result: SubmitResult,
                   lang: str) -> None:
    if result.feedback is None or not tutor.available():
        return
    state = st.session_state.get(state_key(instance_key))
    if state is None or state["result"] is not result:
        state = {"result": result, "explanation": None, "questions": []}
        st.session_state[state_key(instance_key)] = state
    if not result.feedback.correct:
        if state["explanation"] is None and st.button(
                t("Förklara med andra ord"), key=f"forklara_{instance_key}",
                icon=":material/auto_awesome:"):
            with st.spinner(t("Handledaren skriver ett svar.")):
                state["explanation"] = tutor.explain(lang, exercise_id, seed, result)
        if state["explanation"] is not None:
            _show(state["explanation"])
    history = st.container()
    with st.form(f"fraga_{instance_key}", clear_on_submit=True, border=False):
        question = st.text_input(t("Fråga handledaren om den här uppgiften"),
                                 max_chars=tutor.QUESTION_CHARS, key=f"fraga_text_{instance_key}")
        asked = st.form_submit_button(t("Fråga handledaren"), icon=":material/forum:")
    if asked and question.strip():
        with st.spinner(t("Handledaren skriver ett svar.")):
            reply = tutor.answer(lang, exercise_id, seed, result, question)
        state["questions"].append((tutor.clean_question(question), reply))
    with history:
        for asked_text, reply in state["questions"]:
            st.html(f'<p class="ra-ai-question">{escape(t("Din fråga"))}: '
                    f"{escape(asked_text)}</p>")
            _show(reply)
