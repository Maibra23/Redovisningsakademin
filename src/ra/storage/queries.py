"""Basic reads and writes. No business rules; callers own the transaction."""

import uuid
from datetime import date, datetime
from typing import Any

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from ra.storage.models import (
    Attempt,
    ExamResult,
    Learner,
    SimVoucher,
    SimVoucherLine,
    SkillState,
    utc_now,
)


def find_learner_by_hash(session: Session, code_hash: str) -> Learner | None:
    return session.scalar(select(Learner).where(Learner.code_hash == code_hash))


def get_learner(session: Session, learner_id: uuid.UUID) -> Learner | None:
    return session.get(Learner, learner_id)


def create_learner(session: Session, code_hash: str) -> Learner:
    learner = Learner(code_hash=code_hash)
    session.add(learner)
    session.flush()
    return learner


def touch_learner(session: Session, learner_id: uuid.UUID) -> None:
    """Set last_seen_at to now."""
    learner = session.get(Learner, learner_id)
    if learner is not None:
        learner.last_seen_at = utc_now()


def count_learners(session: Session) -> int:
    return session.scalar(select(func.count()).select_from(Learner)) or 0


def delete_sim_vouchers(session: Session, learner_id: uuid.UUID) -> None:
    """Remove every simulator verifikation and its lines for one learner."""
    voucher_ids = select(SimVoucher.id).where(SimVoucher.learner_id == learner_id)
    session.execute(delete(SimVoucherLine).where(SimVoucherLine.voucher_id.in_(voucher_ids)))
    session.execute(delete(SimVoucher).where(SimVoucher.learner_id == learner_id))


def delete_learner(session: Session, learner_id: uuid.UUID) -> None:
    """Remove the learner and every row that belongs to it.

    Child rows are deleted explicitly because SQLite ignores ON DELETE
    CASCADE unless foreign keys are switched on per connection.
    """
    delete_sim_vouchers(session, learner_id)
    for table in (Attempt, SkillState, ExamResult):
        session.execute(delete(table).where(table.learner_id == learner_id))
    session.execute(delete(Learner).where(Learner.id == learner_id))


def get_skill_state(session: Session, learner_id: uuid.UUID, skill_id: str) -> SkillState | None:
    return session.get(SkillState, (learner_id, skill_id))


def skill_states(session: Session, learner_id: uuid.UUID) -> list[SkillState]:
    return list(session.scalars(select(SkillState).where(SkillState.learner_id == learner_id)))


def save_skill_state(session: Session, learner_id: uuid.UUID, skill_id: str,
                     values: dict[str, Any]) -> None:
    """Insert or overwrite the skill_state row with ``values``."""
    row = session.get(SkillState, (learner_id, skill_id))
    if row is None:
        session.add(SkillState(learner_id=learner_id, skill_id=skill_id, **values))
        return
    for column, value in values.items():
        setattr(row, column, value)


def add_attempt(session: Session, values: dict[str, Any]) -> None:
    session.add(Attempt(**values))


def count_attempts(session: Session, learner_id: uuid.UUID, item_id: str, seed: int) -> int:
    """Earlier attempts on one exercise instance (same exercise and seed)."""
    return session.scalar(
        select(func.count()).select_from(Attempt).where(
            Attempt.learner_id == learner_id, Attempt.item_id == item_id, Attempt.seed == seed)
    ) or 0


def total_xp(session: Session, learner_id: uuid.UUID) -> int:
    return session.scalar(
        select(func.coalesce(func.sum(Attempt.xp), 0)).where(Attempt.learner_id == learner_id)
    ) or 0


def save_streak(session: Session, learner_id: uuid.UUID, current: int, longest: int,
                last_active_on: date | None) -> None:
    learner = session.get(Learner, learner_id)
    if learner is not None:
        learner.streak_current = current
        learner.streak_longest = longest
        learner.last_active_on = last_active_on


def attempted_items(session: Session, learner_id: uuid.UUID, skill_id: str) -> set[str]:
    """Exercise ids the learner has attempted for one skill."""
    return set(session.scalars(select(Attempt.item_id).distinct().where(
        Attempt.learner_id == learner_id, Attempt.skill_id == skill_id)))


def count_correct_since(session: Session, learner_id: uuid.UUID, item_id: str,
                        since: datetime) -> int:
    return session.scalar(
        select(func.count()).select_from(Attempt).where(
            Attempt.learner_id == learner_id, Attempt.item_id == item_id,
            Attempt.is_correct.is_(True), Attempt.created_at >= since)
    ) or 0
