"""Nytt scenario on the Övningar page (PRD section 10, architecture section 10).

A new instance of the same exercise, with new figures from the recipe and a
story from ``llm.scenario_text`` around them. The story only replaces the
counterparty and adds a situation and a detail; amounts and accounts are the
recipe's. When the model is off or its answer is refused, the built in story is
used without a message.
"""

import logging

import streamlit as st

from ra.llm import scenario_text
from ra.services import ai, practice
from ra.services.views import ExerciseView

logger = logging.getLogger(__name__)

TYPES = ("kontering", "berakning")


def available() -> bool:
    """The button is an AI control, so it is shown only when the model is configured."""
    return ai.available()


def supported(lang: str, exercise_id: str) -> bool:
    exercise = practice.library(lang).exercises.get(exercise_id)
    return (exercise is not None and exercise.typ in TYPES and exercise.recept is not None
            and scenario_text.supported(exercise.recept))


def _call(prompt: str) -> str | None:
    return ai.complete(prompt, max_tokens=scenario_text.MAX_TOKENS,
                       temperature=scenario_text.TEMPERATURE)


def new_instance(lang: str, exercise_id: str) -> ExerciseView:
    """The same exercise with a new seed and a story; the story is kept for this session."""
    seed = practice.start_exercise(lang, exercise_id).seed
    inst = practice.instance(lang, exercise_id, seed)
    recipe = inst.exercise.recept or ""
    figures = inst.generated.result.figures if inst.generated else {}
    description = figures.get("beskrivning")
    own = description if isinstance(description, str) else None
    story = scenario_text.generate(recipe, scenario_text.category(recipe, own), seed, _call)
    if not story.generated:
        logger.info("Nytt scenario used the built in story for %s", recipe)
    st.session_state[practice.story_key(exercise_id, seed)] = practice.Story(
        story.text, story.generated, own)
    return practice.exercise_view(lang, exercise_id, seed)
