"""Bankavstämning (bank reconciliation).

The bank statement (kontoutdrag) is compared with the bank account in the
huvudbok. Lines match when the amounts are equal and the dates lie at most
three days apart. What is left shows what to book or correct: bank lines with
no ledger entry (for example a bank fee) and ledger entries with no bank line
(for example a payment booked with the wrong amount).
"""

import datetime as dt
from dataclasses import dataclass

from ra.core.money import Money, total

DATE_WINDOW_DAYS = 3
ZERO = Money(0)


@dataclass(frozen=True)
class StatementLine:
    """One line on the kontoutdrag or in the huvudbok; inflow positive, outflow negative."""

    date: dt.date
    amount: Money
    text: str = ""


@dataclass(frozen=True)
class Reconciliation:
    """Result of a bankavstämning.

    ``difference`` is the statement's closing balance minus the ledger balance
    of the bank account; it is zero when everything is booked correctly.
    """

    matched: tuple[tuple[StatementLine, StatementLine], ...]
    bank_only: tuple[StatementLine, ...]
    ledger_only: tuple[StatementLine, ...]
    statement_closing: Money
    ledger_closing: Money

    @property
    def difference(self) -> Money:
        return self.statement_closing - self.ledger_closing


def _best_match(
    bank: StatementLine, candidates: list[StatementLine]
) -> StatementLine | None:
    """Ledger line with the same amount and the closest date within the window."""
    within = [
        c for c in candidates
        if c.amount == bank.amount and abs((c.date - bank.date).days) <= DATE_WINDOW_DAYS
    ]
    return min(within, key=lambda c: abs((c.date - bank.date).days), default=None)


def compare(
    bank_lines: list[StatementLine],
    ledger_lines: list[StatementLine],
    *,
    bank_opening: Money = ZERO,
    ledger_opening: Money = ZERO,
) -> Reconciliation:
    """Match bank lines with ledger lines on amount within a three day window."""
    unmatched_ledger = sorted(ledger_lines, key=lambda line: line.date)
    matched: list[tuple[StatementLine, StatementLine]] = []
    bank_only: list[StatementLine] = []
    for bank in sorted(bank_lines, key=lambda line: line.date):
        match = _best_match(bank, unmatched_ledger)
        if match is None:
            bank_only.append(bank)
        else:
            matched.append((bank, match))
            unmatched_ledger = [line for line in unmatched_ledger if line is not match]
    return Reconciliation(
        matched=tuple(matched),
        bank_only=tuple(bank_only),
        ledger_only=tuple(unmatched_ledger),
        statement_closing=bank_opening + total([line.amount for line in bank_lines]),
        ledger_closing=ledger_opening + total([line.amount for line in ledger_lines]),
    )
