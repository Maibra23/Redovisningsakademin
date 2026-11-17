"""View models the interface renders. Amounts and dates arrive formatted as text."""

import datetime as dt
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
    OBALANS = "obalans"
    TEXT_SAKNAS = "text_saknas"
    DATUM_UTANFOR = "datum_utanfor"
    REDAN_BOKFORD = "redan_bokford"
    INTE_I_INKORGEN = "inte_i_inkorgen"
    FOR_MANGA = "for_manga"


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
    story_by_ai: bool = False


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
    answer: tuple[str, ...] = ()


@dataclass(frozen=True)
class ExamSummaryView:
    """One exam in the list: size, pass mark and the learner's best result so far."""

    exam_id: str
    title: str
    items: int
    pass_percent: int
    best_correct: int | None
    best_percent: int | None
    passed: bool
    attempts: int


@dataclass(frozen=True)
class ExamView:
    """An exam in progress: its items as exercise views, without tips or feedback."""

    exam_id: str
    seed: int
    title: str
    pass_percent: int
    items: tuple[ExerciseView, ...]


@dataclass(frozen=True)
class ExamItemResultView:
    number: int
    correct: bool
    feedback: FeedbackView
    problems: tuple[InputProblem, ...]


@dataclass(frozen=True)
class ExamResultView:
    """Score, pass or fail and the feedback per item after submission."""

    exam_id: str
    title: str
    correct: int
    total: int
    percent: int
    pass_percent: int
    passed: bool
    items: tuple[ExamItemResultView, ...]
    badge: str | None


class TutorStatus(StrEnum):
    """Why the tutor shows text or the page's own message instead."""

    OK = "ok"
    DECLINED = "declined"
    NOT_AVAILABLE = "not_available"
    SESSION_FULL = "session_full"
    DAILY_FULL = "daily_full"


@dataclass(frozen=True)
class TutorReply:
    """Model text that passed the guard, or None and the status the page words."""

    text: str | None
    status: TutorStatus


@dataclass(frozen=True)
class CompanyView:
    """The simulator's company: name, numbers, business, month and redovisningsval."""

    name: str
    orgnr: str
    vat_number: str
    description: str
    month: str
    first_day: str
    last_day: str
    choices: tuple[str, ...]
    first_on: dt.date
    last_on: dt.date


@dataclass(frozen=True)
class InboxItemView:
    """One document in the Inkorg; ``status`` is ny, bokford or rattad."""

    event_id: str
    date: str
    title: str
    kind: str
    counterparty: str
    status: str
    correct: bool | None
    vouchers: tuple[str, ...]
    on: dt.date


@dataclass(frozen=True)
class InboxView:
    current_day: str
    items: tuple[InboxItemView, ...]
    waiting: int
    done: bool


@dataclass(frozen=True)
class SimVoucherView:
    """A stored verifikation with its links: the one it corrects and those correcting it."""

    voucher_id: int | None
    label: str
    date: str
    text: str
    event_id: str | None
    corrects: str | None
    corrected_by: tuple[str, ...]
    voucher: VoucherView


@dataclass(frozen=True)
class SimSubmitResult:
    """Feedback after a booking, or why it was refused (with the totals for an obalans)."""

    problems: tuple[InputProblem, ...] = ()
    totals: VoucherView | None = None
    feedback: FeedbackView | None = None
    voucher_label: str = ""
    xp: int = 0
    total_xp: int = 0
    attempt_no: int = 0


@dataclass(frozen=True)
class LedgerEntryView:
    date: str
    label: str
    text: str
    debet: str
    kredit: str


@dataclass(frozen=True)
class LedgerAccountView:
    """One konto in the huvudbok: ingående balans, each entry and utgående balans."""

    number: int
    name: str
    opening: str
    debet: str
    kredit: str
    closing: str
    entries: tuple[LedgerEntryView, ...]


@dataclass(frozen=True)
class TrialBalanceRowView:
    number: int
    name: str
    debet: str
    kredit: str


@dataclass(frozen=True)
class TrialBalanceView:
    rows: tuple[TrialBalanceRowView, ...]
    total_debet: str
    total_kredit: str
    balanced: bool


@dataclass(frozen=True)
class ReportLineView:
    label: str
    amount: str


@dataclass(frozen=True)
class IncomeStatementView:
    operating: tuple[ReportLineView, ...]
    operating_result: str
    financial: tuple[ReportLineView, ...]
    result_after_financial: str
    tax: tuple[ReportLineView, ...]
    net_result: str


@dataclass(frozen=True)
class BalanceSheetView:
    assets: tuple[ReportLineView, ...]
    total_assets: str
    equity_and_liabilities: tuple[ReportLineView, ...]
    total_equity_and_liabilities: str
    balanced: bool


@dataclass(frozen=True)
class VatReportView:
    """Momsrapport as (fält, amount) pairs; the interface names each fält. The net is
    fält 49, moms to pay when ``to_pay`` and to get back otherwise."""

    rows: tuple[tuple[str, str], ...]
    net: str
    to_pay: bool


@dataclass(frozen=True)
class SimReportsView:
    vouchers: tuple[SimVoucherView, ...]
    ledger: tuple[LedgerAccountView, ...]
    trial_balance: TrialBalanceView
    income: IncomeStatementView
    balance: BalanceSheetView
    vat: VatReportView


@dataclass(frozen=True)
class MissionView:
    """One uppdrag; ``status`` is klart, pagar or vantar. ``next_event`` is the document to
    open next, ``reconciliation`` marks the bankavstämning."""

    mission_id: str
    group: str
    title: str
    description: str
    status: str
    done: int
    total: int
    next_event: str | None
    reconciliation: bool


@dataclass(frozen=True)
class ReconciliationView:
    """Kontoutdrag beside the bank account in the huvudbok, with both balances.

    ``ready`` is true when every document that moves the bank is booked; ``complete``
    when the ledger balance equals the kontoutdrag's closing balance."""

    statement: tuple[StatementLineView, ...]
    ledger: tuple[StatementLineView, ...]
    statement_opening: str
    statement_closing: str
    ledger_closing: str
    difference: str
    ready: bool
    complete: bool
    booked: tuple[SimVoucherView, ...]
    last_on: dt.date


@dataclass(frozen=True)
class SkillAccuracyView:
    skill_id: str
    name: str
    correct: int
    total: int
    percent: int


@dataclass(frozen=True)
class MonthSummaryView:
    """The month's result: reports, accuracy per skill at the first booking, and the badge."""

    complete: bool
    income: IncomeStatementView
    balance: BalanceSheetView
    skills: tuple[SkillAccuracyView, ...]
    badge: bool


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
