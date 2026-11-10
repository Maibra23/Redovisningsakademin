"""Basic reads and writes. No business rules; callers own the transaction."""

import uuid

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
