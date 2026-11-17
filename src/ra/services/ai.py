"""The one way to the language model (CLAUDE.md section 9, architecture section 10).

``ask`` sends engine facts and a task, then cleans the answer and runs the guard.
The caller gets text only when the guard passes; otherwise a status that says
why, so the page shows its built in explanation. Identical prompts are answered
from the cache without counting; a new call is counted against the session and
the app's daily cap before it is sent. The interface hides every AI control
when ``available`` is false.
"""

import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum

import streamlit as st

from ra.llm import budget, clean, client, guard, prompts
from ra.services.practice import library
from ra.storage import queries
from ra.storage.db import new_session

logger = logging.getLogger(__name__)

SESSION_CALLS_KEY = "ai_calls"
LABELS = {"sv": ("Underlag", "Uppgift"), "en": ("Facts", "Task")}


class AiStatus(StrEnum):
    OK = "ok"
    OFF = "off"
    SESSION_FULL = "session_full"
    DAILY_FULL = "daily_full"
    FAILED = "failed"
    REJECTED = "rejected"


@dataclass(frozen=True)
class AiReply:
    """Model text that passed the guard, or None with the reason."""

    text: str | None
    status: AiStatus


def available() -> bool:
    """True when a token is configured; the AI controls are shown only then."""
    return client.is_configured()


def _today() -> datetime:
    return datetime.now(UTC)


def _charge() -> budget.Verdict:
    """Count one call when the budget allows it."""
    used = st.session_state.get(SESSION_CALLS_KEY, 0)
    day = _today().date()
    with new_session() as session, session.begin():
        verdict = budget.verdict(used, queries.llm_calls_on(session, day), budget.daily_cap())
        if verdict is budget.Verdict.OK:
            queries.add_llm_call(session, day)
    if verdict is budget.Verdict.OK:
        st.session_state[SESSION_CALLS_KEY] = used + 1
    return verdict


def system_prompt(language: str) -> str:
    terms = ((term.term, term.engelska) for term in library("sv").glossary)
    return prompts.system_prompt(terms, language)


def _model_text(system: str, user: str, max_tokens: int,
                temperature: float = client.TEMPERATURE) -> AiReply:
    """The model's raw answer: from the cache, or a new call the budget allows."""
    config = client.load_config()
    if config.token is None:
        return AiReply(None, AiStatus.OFF)
    key = client.prompt_key(config, system, user, max_tokens, temperature)
    raw = client.cached(key)
    if raw is None:
        verdict = _charge()
        if verdict is not budget.Verdict.OK:
            return AiReply(None, AiStatus(verdict.value))
        try:
            raw = client.chat(config, system, user, max_tokens, temperature)
        except client.ModelUnavailable as error:
            logger.warning("model call failed: %s", error)
            return AiReply(None, AiStatus.FAILED)
        client.remember(key, raw)
    return AiReply(raw, AiStatus.OK)


def complete(prompt: str, *, max_tokens: int, temperature: float) -> str | None:
    """Raw model text for a structured request (JSON) that the caller validates itself.

    No cleaning and no guard here: the caller must refuse anything it cannot validate.
    """
    return _model_text(system_prompt("sv"), prompt, max_tokens, temperature).text


def ask(task: str, facts: str, *, max_words: int, language: str = "sv",
        max_tokens: int = client.DEFAULT_MAX_TOKENS) -> AiReply:
    """The model's answer to ``task`` built on ``facts``, if the guard lets it through."""
    facts_label, task_label = LABELS.get(language, LABELS["sv"])
    user = f"{facts_label}:\n{facts}\n\n{task_label}:\n{task}"
    reply = _model_text(system_prompt(language), user, max_tokens)
    if reply.text is None:
        return reply
    text = clean.clean(reply.text)
    result = guard.check(text, facts, max_words, language)
    if not result.ok:
        logger.warning("model answer stopped by the guard: %s", ", ".join(result.details))
        return AiReply(None, AiStatus.REJECTED)
    return AiReply(text, AiStatus.OK)
