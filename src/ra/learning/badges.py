"""Märken and Dagens utmaning (PRD section 9). Pure functions over what the
services read from the database; nothing here is stored.

A märke is earned from evidence of competence: a right answer of a kind, a
finished simulator month or a passed prov. Dagens utmaning is five exercises
from five different skills, drawn with a seed from the date, so everyone gets
the same five on the same day.
"""

import datetime as dt
import random
from collections.abc import Iterable
from dataclasses import dataclass

from ra.learning.schemas import Badge, Exercise

CHALLENGE_SIZE = 5
SEED_LIMIT = 2**31


@dataclass(frozen=True)
class Evidence:
    """What the learner has shown: skills answered right, a right kontering, passed
    exams and whether a simulator month is finished."""

    right_skills: frozenset[str] = frozenset()
    right_kontering: bool = False
    passed_exams: frozenset[str] = frozenset()
    month_done: bool = False


def earned(badge: Badge, evidence: Evidence) -> bool:
    rule = badge.villkor
    if rule.typ == "ratt_kontering":
        return evidence.right_kontering
    if rule.typ == "ratt_svar":
        return bool(set(rule.kompetenser) & evidence.right_skills)
    if rule.typ == "manaden_avslutad":
        return evidence.month_done
    return rule.prov in evidence.passed_exams


@dataclass(frozen=True)
class ChallengeItem:
    exercise_id: str
    seed: int


def daily_challenge(exercises: Iterable[Exercise], on_date: dt.date) -> tuple[ChallengeItem, ...]:
    """Five exercises from five different skills (fewer if fewer skills), the same for
    everyone on ``on_date``."""
    rng = random.Random(f"utmaning:{on_date.isoformat()}")
    by_skill: dict[str, list[Exercise]] = {}
    for exercise in sorted(exercises, key=lambda e: e.id):
        by_skill.setdefault(exercise.kompetens, []).append(exercise)
    skills = rng.sample(sorted(by_skill), min(CHALLENGE_SIZE, len(by_skill)))
    return tuple(ChallengeItem(rng.choice(by_skill[skill]).id, rng.randrange(SEED_LIMIT))
                 for skill in skills)
