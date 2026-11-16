"""Evaluate a booked verifikation against the event's recipe solution.

The key is the event's recipe result for the run's seed. The momsomföring is
the exception: its key is computed by core from the learner's own journal, so
a moms booking the learner got wrong earlier is not counted against them twice.
A first booking is graded as an exercise answer (rows merged, alternatives
accepted). After a rättelse the original verifikation and all its rättelser are
graded together on their net effect per account, so any correction that leaves
the right balances is accepted, as in Hitta felet.
"""

from collections.abc import Iterable, Sequence

from ra.core.chart import Chart
from ra.core.ledger import Journal
from ra.core.money import Money
from ra.core.voucher import Side, VoucherLine
from ra.learning.grading import Grade, grade_kontering
from ra.learning.recipes import RecipeContext, RecipeResult
from ra.learning.schemas import Exercise
from ra.simulator.scenario import MONTH_RECIPES, Event, Month, Scenario

ITEM_PREFIX = "sim."
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
