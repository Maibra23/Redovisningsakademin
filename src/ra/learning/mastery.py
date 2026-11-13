"""Mastery per skill (kompetensnivå) and spaced repetition, as in PRD section 6.

States: Ej påbörjad, Övar, Kompetent, Befäst. Kompetent needs at least five
graded attempts, at least 80 procent successes over the latest eight, and
one successful kontering. A success is a correct answer without hints.
Befäst also needs two successful repetitions on later days. A repetition is
a success on or after the due date. Due dates follow 1, 3 and 7 days; a miss
sends the skill back to 1 day and restarts the repetitions. The state is
recomputed from the stored figures after every graded attempt, so it can
also fall back.
"""

import datetime as dt
from dataclasses import dataclass
from enum import StrEnum
from fractions import Fraction


class SkillLevel(StrEnum):
    EJ_PABORJAD = "ej_paborjad"
    OVAR = "ovar"
    KOMPETENT = "kompetent"
    BEFAST = "befast"


MIN_ATTEMPTS = 5
RECENT_WINDOW = 8
COMPETENT_SHARE = Fraction(80, 100)
REPETITIONS_FOR_BEFAST = 2
INTERVAL_DAYS = (1, 3, 7)
KONTERING = "kontering"


@dataclass(frozen=True)
class SkillProgress:
    """Stored state of one skill for one learner."""

    state: SkillLevel = SkillLevel.EJ_PABORJAD
    total: int = 0
    recent: tuple[bool, ...] = ()
    kontering_passed: bool = False
    repetitions_ok: int = 0
    due_on: dt.date | None = None

    @property
    def recent_share(self) -> Fraction:
        """Share of successes among the latest attempts; zero before the first."""
        return Fraction(sum(self.recent), len(self.recent)) if self.recent else Fraction(0)


@dataclass(frozen=True)
class Outcome:
    """One graded attempt as mastery sees it."""

    correct: bool
    hints_used: int
    exercise_type: str
    on_date: dt.date

    @property
    def success(self) -> bool:
        return self.correct and self.hints_used == 0


def _is_competent(total: int, recent: tuple[bool, ...], kontering_passed: bool) -> bool:
    share = Fraction(sum(recent), len(recent)) if recent else Fraction(0)
    return total >= MIN_ATTEMPTS and share >= COMPETENT_SHARE and kontering_passed


def _state(total: int, recent: tuple[bool, ...], kontering_passed: bool,
           repetitions: int) -> SkillLevel:
    if _is_competent(total, recent, kontering_passed):
        return SkillLevel.BEFAST if repetitions >= REPETITIONS_FOR_BEFAST else SkillLevel.KOMPETENT
    return SkillLevel.OVAR if total > 0 else SkillLevel.EJ_PABORJAD


def next_due(on_date: dt.date, success: bool, repetitions: int) -> dt.date:
    """1, 3 and then 7 days after a success; 1 day after a miss."""
    if not success:
        return on_date + dt.timedelta(days=INTERVAL_DAYS[0])
    step = min(repetitions, len(INTERVAL_DAYS) - 1)
    return on_date + dt.timedelta(days=INTERVAL_DAYS[step])


def update(progress: SkillProgress, outcome: Outcome) -> SkillProgress:
    """New skill state after one graded attempt."""
    success = outcome.success
    was_due = progress.due_on is not None and outcome.on_date >= progress.due_on
    if not success:
        repetitions = 0
    elif was_due:
        repetitions = progress.repetitions_ok + 1
    else:
        repetitions = progress.repetitions_ok
    total = progress.total + 1
    recent = (progress.recent + (success,))[-RECENT_WINDOW:]
    kontering_passed = progress.kontering_passed or (
        success and outcome.exercise_type == KONTERING)
    return SkillProgress(
        state=_state(total, recent, kontering_passed, repetitions),
        total=total,
        recent=recent,
        kontering_passed=kontering_passed,
        repetitions_ok=repetitions,
        due_on=next_due(outcome.on_date, success, repetitions),
    )
