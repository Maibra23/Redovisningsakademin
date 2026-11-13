"""Shared progress writes: one attempt row and the svit, used by every graded context.

Practice, the simulator, prov and Dagens utmaning all record attempts here so
the rules for the svit and the XP cap live in one place. Callers own the
transaction and pass an open session.
"""

import datetime as dt
import uuid
from typing import Any

from sqlalchemy.orm import Session

from ra.learning import gamification
from ra.storage import queries


class ProgressError(LookupError):
    """The learner does not exist."""


def correct_today(session: Session, learner_id: uuid.UUID, item_id: str,
                  on_date: dt.date, tz: dt.tzinfo) -> int:
    """Correct attempts on one exercise since local midnight of ``on_date``."""
    since = dt.datetime.combine(on_date, dt.time.min, tzinfo=tz).astimezone(dt.UTC)
    return queries.count_correct_since(session, learner_id, item_id, since)


def record_attempt(session: Session, learner_id: uuid.UUID, values: dict[str, Any],
                   on_date: dt.date) -> None:
    """Store the attempt and count ``on_date`` toward the svit."""
    learner = queries.get_learner(session, learner_id)
    if learner is None:
        raise ProgressError(f"Unknown learner {learner_id}")
    queries.add_attempt(session, {"learner_id": learner_id, **values})
    streak = gamification.update_streak(gamification.Streak(
        learner.streak_current, learner.streak_longest, learner.last_active_on), on_date)
    queries.save_streak(session, learner_id, streak.current, streak.longest,
                        streak.last_active_on)
