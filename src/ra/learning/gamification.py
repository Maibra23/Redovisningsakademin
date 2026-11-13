"""XP, nivåer and svit (streak), as in PRD section 9. Points follow demonstrated skill.

XP per graded attempt by difficulty: full on a correct first attempt without
hints, half (rounded down) on a correct first attempt with hints, none for a
wrong answer or for any later attempt on the same exercise, because the
feedback after the first attempt shows the solution.
"""

import datetime as dt
from collections.abc import Mapping, Set
from dataclasses import dataclass

XP_BY_DIFFICULTY: Mapping[str, int] = {"grund": 10, "medel": 20, "avancerad": 35}


@dataclass(frozen=True)
class Level:
    """A nivå: the XP it needs and the role target whose skills must be at Kompetent."""

    name: str
    min_xp: int
    role: str | None = None


# XP thresholds are the app's own choice (PRD section 9 names the levels only).
LEVELS: tuple[Level, ...] = (
    Level("Praktikant", 0),
    Level("Bokföringsbiträde", 250),
    Level("Ekonomiassistent", 750, "ekonomiassistent"),
    Level("Redovisningsassistent", 1500, "redovisningsassistent"),
    Level("Redovisningsekonom", 3000, "redovisningsassistent"),
)


def xp_for(difficulty: str, correct: bool, attempt_no: int, hints_used: int) -> int:
    """XP for one graded attempt."""
    if not correct or attempt_no > 1:
        return 0
    full = XP_BY_DIFFICULTY[difficulty]
    return full if hints_used == 0 else full // 2


def level(xp: int, competent_skills: Set[str], roles: Mapping[str, Set[str]]) -> Level:
    """Highest level reached in order; a gated level also needs its role's skills."""
    reached = LEVELS[0]
    for candidate in LEVELS[1:]:
        required = roles.get(candidate.role) if candidate.role else frozenset()
        gate_open = required is not None and required <= competent_skills
        if xp < candidate.min_xp or not gate_open:
            break
        reached = candidate
    return reached


@dataclass(frozen=True)
class Streak:
    """Svit: days in a row with at least one graded activity."""

    current: int = 0
    longest: int = 0
    last_active_on: dt.date | None = None


def update_streak(streak: Streak, today: dt.date) -> Streak:
    """Count today once; a gap of more than one day starts the svit again."""
    if streak.last_active_on == today:
        return streak
    yesterday = today - dt.timedelta(days=1)
    current = streak.current + 1 if streak.last_active_on == yesterday else 1
    return Streak(current, max(streak.longest, current), today)
