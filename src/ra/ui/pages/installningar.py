"""Inställningar: language, the sparkod with a copy button, Återställ simulatorn and
Radera min progression, each with a confirmation (architecture section 6).

Layout and widgets only; the actions are services.simulator.reset and
services.learner.delete_all. Återställ starts a new simulator run; the old
run's verifikationer stay stored, so nothing booked is changed or lost.
"""

import uuid
from urllib.parse import urlencode, urlsplit

import streamlit as st

from ra.services import learner, simulator
from ra.ui.i18n import LANG_KEY, LANGUAGES, get_lang, t
from ra.ui.theme import info_box, page_title

LANGUAGE_CHOICE_KEY = "installning_sprak"
MESSAGE_KEY = "installning_meddelande"


def _choose_language() -> None:
    st.session_state[LANG_KEY] = st.session_state[LANGUAGE_CHOICE_KEY]


def _link(code: str) -> str:
    """The app's address with the sparkod, from the address the browser used."""
    try:
        parts = urlsplit(st.context.url or "")
    except (AttributeError, ValueError):
        return f"?{urlencode({learner.CODE_PARAM: code})}"
    base = f"{parts.scheme}://{parts.netloc}/" if parts.netloc else ""
    return f"{base}?{urlencode({learner.CODE_PARAM: code})}"


def _language() -> None:
    st.subheader(t("Språk"), anchor=False)
    st.session_state[LANGUAGE_CHOICE_KEY] = get_lang()
    st.radio(t("Språk"), list(LANGUAGES), format_func=LANGUAGES.__getitem__,
             key=LANGUAGE_CHOICE_KEY, horizontal=True, on_change=_choose_language,
             label_visibility="collapsed")


def _code() -> None:
    st.subheader(t("Din sparkod"), anchor=False)
    st.write(t("Länken nedan ger tillgång till din progression. Spara den som bokmärke, eller "
               "öppna den på en annan enhet för att fortsätta där. Den som får länken kan se "
               "och ändra din progression, så dela den inte."))
    code = learner.current_code()
    if code:
        st.code(_link(code), language=None)
        st.caption(t("Kopiera länken med knappen till höger i rutan."))


def _reset(learner_id: uuid.UUID) -> None:
    st.subheader(t("Återställ simulatorn"), anchor=False)
    st.write(t("Simulatorn börjar om med samma företag och nya belopp. Din övriga progression "
               "påverkas inte."))
    sure = st.checkbox(t("Jag vill börja om simulatorn"), key="bekrafta_aterstall")
    if st.button(t("Återställ simulatorn"), disabled=not sure, key="aterstall_simulatorn"):
        simulator.reset(learner_id)
        st.session_state[MESSAGE_KEY] = "Simulatorn har börjat om med nya belopp."
        st.session_state.pop("bekrafta_aterstall", None)
        st.rerun()


def _delete(learner_id: uuid.UUID) -> None:
    st.subheader(t("Radera min progression"), anchor=False)
    st.write(t("Allt du har gjort raderas: svar, nivåer, XP, prov och simulatorn. Sparkoden "
               "slutar att fungera och du får en ny."))
    sure = st.checkbox(t("Jag förstår att min progression raderas och inte går att få tillbaka"),
                       key="bekrafta_radera")
    if st.button(t("Radera min progression"), disabled=not sure, type="primary",
                 key="radera_progression"):
        learner.delete_all(learner_id)
        st.session_state[MESSAGE_KEY] = "Din progression är raderad. Du har fått en ny sparkod."
        st.session_state.pop("bekrafta_radera", None)
        st.rerun()


def render() -> None:
    learner_id = learner.get_or_create()
    page_title(t("Min utveckling"), t("Inställningar"),
               t("Språk, din sparkod och att börja om."))
    message = st.session_state.pop(MESSAGE_KEY, None)
    if message:
        st.success(t(message), icon=":material/check:")
    _language()
    _code()
    _reset(learner_id)
    info_box(t("Appen sparar inga personuppgifter. Det som sparas är dina svar och din "
               "progression, kopplade till sparkoden."))
    _delete(learner_id)
