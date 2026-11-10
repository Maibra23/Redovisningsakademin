"""Database tables for learner state (architecture section 5).

Only learner state is stored; content stays in files and is referred to by
identifier. Amount columns are integer öre and end in ``_ore``.
"""

import uuid
from datetime import UTC, date, datetime

from sqlalchemy import (
    JSON,
    BigInteger,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Uuid,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

# BIGINT keys on PostgreSQL; SQLite only autoincrements a plain INTEGER key.
ROW_ID = BigInteger().with_variant(Integer, "sqlite")


def utc_now() -> datetime:
    return datetime.now(UTC)


class Base(DeclarativeBase):
    pass


def _learner_fk() -> Mapped[uuid.UUID]:
    return mapped_column(Uuid, ForeignKey("learner.id", ondelete="CASCADE"), index=True)


def _created_at() -> Mapped[datetime]:
    return mapped_column(DateTime(timezone=True), default=utc_now)


class Learner(Base):
    __tablename__ = "learner"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    code_hash: Mapped[str] = mapped_column(String(64), unique=True)
    created_at: Mapped[datetime] = _created_at()
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    streak_current: Mapped[int] = mapped_column(Integer, default=0)
    streak_longest: Mapped[int] = mapped_column(Integer, default=0)
    last_active_on: Mapped[date | None] = mapped_column(Date)
    settings: Mapped[dict] = mapped_column(JSON, default=dict)


class Attempt(Base):
    __tablename__ = "attempt"
    __table_args__ = (
        Index("ix_attempt_learner_skill_time", "learner_id", "skill_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(ROW_ID, primary_key=True)
    learner_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("learner.id", ondelete="CASCADE")
    )  # indexed through ix_attempt_learner_skill_time
    item_id: Mapped[str] = mapped_column(String(64))
    skill_id: Mapped[str] = mapped_column(String(32))
    context: Mapped[str] = mapped_column(String(16))
    difficulty: Mapped[str] = mapped_column(String(16))
    seed: Mapped[int] = mapped_column(BigInteger)
    is_correct: Mapped[bool]
    attempt_no: Mapped[int] = mapped_column(Integer, default=1)
    hints_used: Mapped[int] = mapped_column(Integer, default=0)
    error_codes: Mapped[list] = mapped_column(JSON, default=list)
    xp: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = _created_at()


class SkillState(Base):
    __tablename__ = "skill_state"

    learner_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("learner.id", ondelete="CASCADE"), primary_key=True
    )
    skill_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    state: Mapped[str] = mapped_column(String(16))
    total: Mapped[int] = mapped_column(Integer, default=0)
    recent: Mapped[list] = mapped_column(JSON, default=list)
    kontering_passed: Mapped[bool] = mapped_column(default=False)
    repetitions_ok: Mapped[int] = mapped_column(Integer, default=0)
    due_on: Mapped[date | None] = mapped_column(Date)


class SimVoucher(Base):
    __tablename__ = "sim_voucher"

    id: Mapped[int] = mapped_column(ROW_ID, primary_key=True)
    learner_id: Mapped[uuid.UUID] = _learner_fk()
    sim_seed: Mapped[int] = mapped_column(BigInteger)
    series: Mapped[str] = mapped_column(String(8))
    number: Mapped[int] = mapped_column(Integer)
    entry_date: Mapped[date] = mapped_column(Date)
    text: Mapped[str] = mapped_column(String(200))
    document_id: Mapped[str | None] = mapped_column(String(64))
    corrects_id: Mapped[int | None] = mapped_column(
        ROW_ID, ForeignKey("sim_voucher.id", ondelete="SET NULL")
    )
    created_at: Mapped[datetime] = _created_at()


class SimVoucherLine(Base):
    __tablename__ = "sim_voucher_line"
    __table_args__ = (
        CheckConstraint(
            "(debit_ore > 0 AND credit_ore = 0) OR (credit_ore > 0 AND debit_ore = 0)",
            name="ck_sim_voucher_line_one_side",
        ),
    )

    id: Mapped[int] = mapped_column(ROW_ID, primary_key=True)
    voucher_id: Mapped[int] = mapped_column(
        ROW_ID, ForeignKey("sim_voucher.id", ondelete="CASCADE"), index=True
    )
    account_no: Mapped[int] = mapped_column(Integer)
    debit_ore: Mapped[int] = mapped_column(BigInteger, default=0)
    credit_ore: Mapped[int] = mapped_column(BigInteger, default=0)


class ExamResult(Base):
    __tablename__ = "exam_result"

    id: Mapped[int] = mapped_column(ROW_ID, primary_key=True)
    learner_id: Mapped[uuid.UUID] = _learner_fk()
    exam_id: Mapped[str] = mapped_column(String(32))
    seed: Mapped[int] = mapped_column(BigInteger)
    score: Mapped[int] = mapped_column(Integer)
    passed: Mapped[bool]
    created_at: Mapped[datetime] = _created_at()
