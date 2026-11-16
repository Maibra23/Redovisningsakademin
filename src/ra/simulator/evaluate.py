"""Evaluate a booked verifikation against the event's recipe solution.

The key is the event's recipe result for the run's seed. The momsomföring is
the exception: its key is computed by core from the learner's own journal, so
a moms booking the learner got wrong earlier is not counted against them twice.
A first booking is graded as an exercise answer (rows merged, alternatives
accepted). After a rättelse the original verifikation and all its rättelser are
graded together on their net effect per account, so any correction that leaves
the right balances is accepted, as in Hitta felet.

The bankavstämning is graded like the Avstämning exercise: the marked
kontoutdrag lines must be the ones core's reconciliation leaves unmatched
against the bank account, and the bookings together must have the effect of
the two planted rows.
"""

from collections.abc import Iterable, Sequence
from itertools import combinations
from types import MappingProxyType

from ra.core.chart import Chart
from ra.core.ledger import Journal
from ra.core.money import Money, total
from ra.core.reconciliation import StatementLine, compare
from ra.core.voucher import Side, Voucher, VoucherLine
from ra.learning.grading import ErrorCode, Grade, grade_kontering
from ra.learning.recipes import RecipeContext, RecipeResult
from ra.learning.schemas import Exercise
from ra.simulator.scenario import BANK, MONTH_RECIPES, Event, Mission, Month, Scenario

ITEM_PREFIX = "sim."
RECONCILIATION_ID = "avstamning"  # document id of the bookings made in the bankavstämning
RECONCILIATION_TEXT = "Bankavstämning"
DIFFICULTY = "medel"
# Month recipes whose key depends on what the learner has booked so far.
FROM_LEARNER_JOURNAL = frozenset({"momsomforing_manad"})


class EvaluationError(LookupError):
    """The event is not part of the scenario."""


def key(ctx: RecipeContext, scenario: Scenario, month: Month, event: Event,
        journal: Journal) -> RecipeResult:
    """The accepted solution for ``event``; ``journal`` holds the learner's other bookings."""
    realised = next((r for r in month.events if r.event.id == event.id), None)
    if realised is None:
        raise EvaluationError(f"Unknown event {event.id}")
    if event.recept in FROM_LEARNER_JOURNAL:
        result = MONTH_RECIPES[event.recept](ctx, scenario, journal, event.datum)
        return RecipeResult(result.figures, result.voucher, realised.result.alternatives)
    return realised.result


def as_exercise(event: Event) -> Exercise:
    """The event as a kontering exercise, so grading, XP, mastery and feedback are shared."""
    return Exercise(id=f"{ITEM_PREFIX}{event.id}", typ="kontering", kompetens=event.kompetens,
                    niva=DIFFICULTY, regel=event.regel, tips=event.tips, recept=event.recept)


def grade_booking(chart: Chart, solution: RecipeResult, lines: Iterable[VoucherLine]) -> Grade:
    """A first booking, graded as an exercise answer."""
    return grade_kontering(chart, lines, solution)


def net_effect(vouchers: Iterable[Sequence[VoucherLine]]) -> tuple[VoucherLine, ...]:
    """The combined effect per account of a verifikation and its rättelser."""
    effect: dict[int, Money] = {}
    for lines in vouchers:
        for line in lines:
            signed = line.amount if line.side is Side.DEBET else -line.amount
            effect[line.account] = effect.get(line.account, Money.zero()) + signed
    return tuple(VoucherLine(n, Side.DEBET if m.ore > 0 else Side.KREDIT, Money(abs(m.ore)))
                 for n, m in sorted(effect.items()) if m.ore)


def grade_group(chart: Chart, solution: RecipeResult,
                vouchers: Sequence[Sequence[VoucherLine]]) -> Grade:
    """One verifikation alone is graded as booked; with rättelser, on the net effect."""
    if len(vouchers) == 1:
        return grade_booking(chart, solution, vouchers[0])
    return grade_kontering(chart, net_effect(vouchers), solution)


def bank_lines(journal: Journal) -> list[StatementLine]:
    """Each verifikation's movement on the bank account, as lines to reconcile."""
    lines = []
    for voucher in journal.vouchers:
        moved = total([ln.amount if ln.side is Side.DEBET else -ln.amount
                       for ln in voucher.lines if ln.account == BANK])
        if moved.ore:
            lines.append(StatementLine(voucher.date, moved, voucher.text))
    return lines


def statement_lines(month: Month) -> list[StatementLine]:
    return [StatementLine(row.on_date, row.amount, row.text) for row in month.statement]


def differing(month: Month, journal: Journal) -> frozenset[int]:
    """Kontoutdrag lines (by index) with no matching entry on the bank account."""
    statement = statement_lines(month)
    position = {id(line): index for index, line in enumerate(statement)}
    result = compare(statement, bank_lines(journal))
    return frozenset(position[id(line)] for line in result.bank_only)


def reconciliation_key(scenario: Scenario, month: Month) -> RecipeResult:
    """What the bankavstämning should book: the combined effect of the planted rows."""
    lines = net_effect(row.planted.voucher.lines for row in month.planted if row.planted)
    voucher = Voucher(scenario.company.serie, scenario.month_end, RECONCILIATION_TEXT, lines)
    return RecipeResult(MappingProxyType({}), voucher)


def grade_reconciliation(chart: Chart, scenario: Scenario, month: Month,
                         vouchers: Iterable[Sequence[VoucherLine]]) -> Grade:
    """The bankavstämning bookings together against the planted rows.

    Bookings that cover some of the planted rows exactly are not wrong, only
    incomplete, so they are graded RAD_SAKNAS rather than by the account pairing.
    """
    effect = net_effect(vouchers)
    grade = grade_kontering(chart, effect, reconciliation_key(scenario, month))
    if grade.correct:
        return grade
    planted = [row.planted.voucher.lines for row in month.planted if row.planted]
    for size in range(1, len(planted)):
        if any(net_effect(subset) == effect for subset in combinations(planted, size)):
            return Grade(False, (ErrorCode.RAD_SAKNAS,))
    return grade


def reconciliation_exercise(mission: Mission) -> Exercise:
    """The bankavstämning as an avstämning exercise, for XP, mastery and feedback."""
    return Exercise(id=f"{ITEM_PREFIX}{RECONCILIATION_ID}", typ="avstamning",
                    kompetens=mission.kompetens or "", niva=DIFFICULTY, regel=mission.regel or "",
                    tips=mission.tips or "")
