"""View models the interface renders. Amounts and dates arrive formatted as text."""

from collections.abc import Iterable
from dataclasses import dataclass
from enum import StrEnum

from ra.core.chart import Chart
from ra.core.money import Money, total
from ra.core.voucher import Side, VoucherLine
from ra.learning.documents import Document
from ra.learning.feedback import Feedback
from ra.learning.mastery import SkillLevel
from ra.services.formatting import format_date, format_ore


class InputProblem(StrEnum):
    """Why an answer could not be read; the interface words each one."""

    BELOPP_OLASLIGT = "belopp_olasligt"
    KONTO_SAKNAS = "konto_saknas"
    BADA_SIDOR = "bada_sidor"
    TOMT_SVAR = "tomt_svar"


@dataclass(frozen=True)
class RowInput:
    """One row of the verifikation grid as typed: account label, debet and kredit text."""

    account: str | None
    debet: str = ""
    kredit: str = ""


@dataclass(frozen=True)
class AvstamningInput:
    """Avstämning answer: indexes of the marked kontoutdrag lines and the booked rows."""

    marked: frozenset[int]
    rows: tuple[RowInput, ...]


@dataclass(frozen=True)
class AccountOption:
    number: int
    label: str


@dataclass(frozen=True)
class VoucherRowView:
    account: int
    name: str
    debet: str
    kredit: str


@dataclass(frozen=True)
class VoucherView:
    """Konto, kontonamn, debet, kredit, totals and whether the verifikation balances."""

    rows: tuple[VoucherRowView, ...]
    total_debet: str
    total_kredit: str
    difference: str
    balanced: bool


@dataclass(frozen=True)
class DocumentView:
    kind: str
    title: str
    counterparty: str
    date: str
    text: str
    rows: tuple[tuple[str, str | None], ...]
    totals: tuple[tuple[str, str | None], ...]


@dataclass(frozen=True)
class StatementLineView:
    """A line on a kontoutdrag or in the huvudbok: date, text and signed amount."""

    index: int
    date: str
    text: str
    amount: str


@dataclass(frozen=True)
class ExerciseView:
    exercise_id: str
    seed: int
    typ: str
    skill_id: str
    difficulty: str
    instruction: str
    hint: str
    document: DocumentView | None = None
    question: str = ""
    options: tuple[str, ...] = ()
    categories: tuple[str, ...] = ()
    items: tuple[str, ...] = ()
    booked: VoucherView | None = None
    statement: tuple[StatementLineView, ...] = ()
    ledger: tuple[StatementLineView, ...] = ()


@dataclass(frozen=True)
class SkillChoice:
    skill_id: str
    name: str
    difficulties: tuple[str, ...]


@dataclass(frozen=True)
class SkillView:
    skill_id: str
    name: str
    state: SkillLevel
    total: int
    recent_percent: int | None
    due_on: str | None


@dataclass(frozen=True)
class FeedbackView:
    correct: bool
    heading: str
    what: str
    why: str
    treatment: str
    treatment_voucher: VoucherView | None
    notes: tuple[str, ...]
    rule_title: str
    rule_reference: str
    rule_url: str
    tip: str
    codes: tuple[str, ...]


@dataclass(frozen=True)
class SubmitResult:
    """Feedback and progress after a graded answer, or the problems that stopped grading."""

    problems: tuple[InputProblem, ...] = ()
    feedback: FeedbackView | None = None
    xp: int = 0
    total_xp: int = 0
    attempt_no: int = 0
    xp_capped: bool = False
    skill: SkillView | None = None


def _amount_text(amount: Money) -> str:
    return format_ore(amount.ore) if amount.ore else ""


def voucher_view(chart: Chart, lines: Iterable[VoucherLine]) -> VoucherView:
    rows = tuple(lines)
    debet = total([ln.amount for ln in rows if ln.side is Side.DEBET])
    kredit = total([ln.amount for ln in rows if ln.side is Side.KREDIT])
    return VoucherView(
        rows=tuple(
            VoucherRowView(
                account=ln.account,
                name=chart[ln.account].name if ln.account in chart else "",
                debet=_amount_text(ln.amount) if ln.side is Side.DEBET else "",
                kredit=_amount_text(ln.amount) if ln.side is Side.KREDIT else "",
            ) for ln in rows
        ),
        total_debet=format_ore(debet.ore),
        total_kredit=format_ore(kredit.ore),
        difference=format_ore((debet - kredit).ore),
        balanced=debet == kredit,
    )


def document_view(document: Document) -> DocumentView:
    def rows(items: Iterable) -> tuple[tuple[str, str | None], ...]:
        return tuple((r.text, format_ore(r.amount.ore) if r.amount else None) for r in items)

    return DocumentView(document.kind, document.title, document.counterparty,
                        format_date(document.date), document.text, rows(document.rows),
                        rows(document.totals))


def feedback_view(chart: Chart, feedback: Feedback) -> FeedbackView:
    lines = feedback.treatment.lines
    return FeedbackView(
        correct=feedback.correct,
        heading=feedback.heading,
        what=feedback.what,
        why=feedback.why,
        treatment=feedback.treatment.text,
        treatment_voucher=voucher_view(chart, lines) if lines else None,
        notes=feedback.treatment.notes,
        rule_title=feedback.rule.title,
        rule_reference=feedback.rule.reference,
        rule_url=feedback.rule.source_url,
        tip=feedback.tip,
        codes=feedback.codes,
    )
