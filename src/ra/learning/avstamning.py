"""Avstämning: compare a kontoutdrag with the bank account in the huvudbok.

A month of payments is generated from the payment recipes. Two differences
are planted: a bank fee on the kontoutdrag that is missing in the huvudbok,
and one payment booked with two digits swapped. ``core.reconciliation``
finds the statement lines without a ledger match; the learner must mark
exactly those and book what makes the ledger balance equal the statement.
The booking is graded on its effect per account, so one combined
verifikation or one per difference are both accepted.
"""

import datetime as dt
import random
from collections.abc import Iterable, Mapping, Set
from dataclasses import dataclass

from ra.core.chart import Chart
from ra.core.money import Money, total
from ra.core.reconciliation import StatementLine, compare
from ra.core.voucher import IssueCode, Side, Voucher, VoucherLine, validate
from ra.learning import recipes
from ra.learning.grading import ErrorCode, Grade, classify
from ra.learning.hitta_felet import transpositions

BANK = recipes.BANK
PAYMENT_RECIPES = ("inbetalning_kund", "utbetalning_leverantor")
FEE_RECIPE = "bankavgift"
MIN_PAYMENTS, MAX_PAYMENTS = 4, 6
LAST_PAYMENT_DAY, FEE_DAY = 25, 28
OPENING_ORE = (5_000_000, 20_000_000)
CORRECTION_TEXT = "Rättelse efter bankavstämning"
FALLBACK_DELTA = Money(9_000)

Position = tuple[int, Side]


@dataclass(frozen=True)
class ReconciliationTask:
    """Kontoutdrag and huvudbok lines for 1930, the planted differences and the key."""

    opening: Money
    statement: tuple[StatementLine, ...]
    ledger: tuple[StatementLine, ...]
    differing: frozenset[int]
    key: Voucher


def _signed_bank(voucher: Voucher) -> Money:
    return total([ln.amount if ln.side is Side.DEBET else -ln.amount
                  for ln in voucher.lines if ln.account == BANK])


def _counter_account(voucher: Voucher) -> int:
    return next(ln.account for ln in voucher.lines if ln.account != BANK)


def _payments(ctx: recipes.RecipeContext, rng: random.Random,
              month: tuple[int, int]) -> list[tuple[StatementLine, int]]:
    """Signed bank lines with their counter account, sorted by date."""
    found = []
    for _ in range(rng.randint(MIN_PAYMENTS, MAX_PAYMENTS)):
        voucher = recipes.generate(ctx, rng.choice(PAYMENT_RECIPES), rng.randrange(2**31)
                                   ).result.voucher
        on = dt.date(*month, rng.randint(1, LAST_PAYMENT_DAY))
        found.append((StatementLine(on, _signed_bank(voucher), voucher.text),
                      _counter_account(voucher)))
    return sorted(found, key=lambda item: item[0].date)


def _correction_lines(difference: Money, counter: int) -> tuple[VoucherLine, ...]:
    """Bring the bank account up or down by ``difference`` against ``counter``."""
    amount = Money(abs(difference.ore))
    if difference.ore > 0:
        return (VoucherLine(BANK, Side.DEBET, amount), VoucherLine(counter, Side.KREDIT, amount))
    return (VoucherLine(counter, Side.DEBET, amount), VoucherLine(BANK, Side.KREDIT, amount))


def generate(ctx: recipes.RecipeContext, seed: int) -> ReconciliationTask:
    """A month on the kontoutdrag with one missing bank fee and one wrong amount in the ledger."""
    rng = random.Random(seed)
    month = (recipes.EXERCISE_YEAR, rng.randint(1, 12))
    payments = _payments(ctx, rng, month)
    wrong_index = rng.randrange(len(payments))
    true_line, counter = payments[wrong_index]
    true_abs = Money(abs(true_line.amount.ore))
    options = transpositions(true_abs)
    booked_abs = rng.choice(options) if options else true_abs + FALLBACK_DELTA
    booked = booked_abs if true_line.amount.ore > 0 else -booked_abs
    fee_voucher = recipes.generate(ctx, FEE_RECIPE, rng.randrange(2**31)).result.voucher
    fee = StatementLine(dt.date(*month, FEE_DAY), _signed_bank(fee_voucher), fee_voucher.text)
    statement = tuple(line for line, _ in payments) + (fee,)
    ledger_lines = tuple(
        StatementLine(line.date, booked, line.text) if i == wrong_index else line
        for i, (line, _) in enumerate(payments)
    )
    opening = Money(rng.randrange(OPENING_ORE[0], OPENING_ORE[1], 100))
    result = compare(list(statement), list(ledger_lines), bank_opening=opening,
                     ledger_opening=opening)
    differing = frozenset(statement.index(line) for line in result.bank_only)
    key_lines = (_correction_lines(fee.amount, fee_voucher.lines[0].account)
                 + _correction_lines(true_line.amount - booked, counter))
    key = Voucher(recipes.SERIES, fee.date, CORRECTION_TEXT, key_lines)
    return ReconciliationTask(opening, statement, ledger_lines, differing, key)


def _effect(lines: Iterable[VoucherLine]) -> dict[int, Money]:
    signed: dict[int, Money] = {}
    for ln in lines:
        value = ln.amount if ln.side is Side.DEBET else -ln.amount
        signed[ln.account] = signed.get(ln.account, Money.zero()) + value
    return {n: m for n, m in signed.items() if m.ore != 0}


def _positions(effect: Mapping[int, Money]) -> dict[Position, Money]:
    return {(n, Side.DEBET if m.ore > 0 else Side.KREDIT): Money(abs(m.ore))
            for n, m in effect.items()}


@dataclass(frozen=True)
class ReconciliationGrade:
    marks_correct: bool
    booking: Grade
    remaining_difference: Money

    @property
    def correct(self) -> bool:
        return self.marks_correct and self.booking.correct


def grade(chart: Chart, task: ReconciliationTask, marked: Set[int],
          lines: Iterable[VoucherLine]) -> ReconciliationGrade:
    """Marks must equal the differing statement lines; bookings must close the difference."""
    answer = tuple(lines)
    on_date = task.statement[-1].date
    bank_change = _effect(answer).get(BANK, Money.zero())
    after = compare(list(task.statement),
                    list(task.ledger) + [StatementLine(on_date, bank_change)],
                    bank_opening=task.opening, ledger_opening=task.opening)
    issues = validate(chart, Voucher(recipes.SERIES, on_date, CORRECTION_TEXT, answer))
    expected = _effect(task.key.lines)
    if any(i.code is IssueCode.UNBALANCED for i in issues):
        booking = Grade(False, (ErrorCode.OBALANS,))
    elif _effect(answer) == expected and not issues:
        booking = Grade(True)
    else:
        booking = Grade(False, tuple(classify(chart, _positions(_effect(answer)),
                                              _positions(expected), {})))
    return ReconciliationGrade(set(marked) == set(task.differing), booking, after.difference)
