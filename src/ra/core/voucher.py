"""Verifikation (voucher) and its validation.

A verifikation records one business event as lines on accounts, each on the
debet or kredit side. A correct verifikation has a text, at least two lines,
only known accounts, positive amounts, and equal debet and kredit totals.
"""

import datetime as dt
from collections.abc import Container
from dataclasses import dataclass
from enum import Enum

from ra.core.money import Money, total


class Side(Enum):
    """Debet or kredit side of a kontering."""

    DEBET = "debet"
    KREDIT = "kredit"


class IssueCode(Enum):
    """Why a verifikation cannot be posted."""

    UNBALANCED = "unbalanced"
    TOO_FEW_LINES = "too_few_lines"
    UNKNOWN_ACCOUNT = "unknown_account"
    NON_POSITIVE_AMOUNT = "non_positive_amount"
    MISSING_TEXT = "missing_text"


@dataclass(frozen=True)
class VoucherKey:
    """Identity of a verifikation: series and number, for example A 12."""

    series: str
    number: int


@dataclass(frozen=True)
class VoucherLine:
    """One kontering row: account, side and a positive amount."""

    account: int
    side: Side
    amount: Money


@dataclass(frozen=True)
class Voucher:
    """Verifikation. ``number`` is None until the journal assigns it.

    ``corrects`` points at the verifikation this one corrects (rättelse);
    a posted verifikation is never changed.
    """

    series: str
    date: dt.date
    text: str
    lines: tuple[VoucherLine, ...]
    number: int | None = None
    corrects: VoucherKey | None = None

    def side_total(self, side: Side) -> Money:
        """Summa debet or summa kredit."""
        return total([line.amount for line in self.lines if line.side is side])


@dataclass(frozen=True)
class Issue:
    """One validation finding; ``account`` is set when the issue concerns one line."""

    code: IssueCode
    account: int | None = None


MIN_LINES = 2


def validate(chart: Container[int], voucher: Voucher) -> list[Issue]:
    """All reasons the verifikation cannot be posted; empty when it is valid.

    ``chart`` is anything that answers ``account in chart`` (the kontoplan).
    """
    issues: list[Issue] = []
    if not voucher.text.strip():
        issues.append(Issue(IssueCode.MISSING_TEXT))
    if len(voucher.lines) < MIN_LINES:
        issues.append(Issue(IssueCode.TOO_FEW_LINES))
    for line in voucher.lines:
        if line.account not in chart:
            issues.append(Issue(IssueCode.UNKNOWN_ACCOUNT, line.account))
        if line.amount.ore <= 0:
            issues.append(Issue(IssueCode.NON_POSITIVE_AMOUNT, line.account))
    if voucher.side_total(Side.DEBET) != voucher.side_total(Side.KREDIT):
        issues.append(Issue(IssueCode.UNBALANCED))
    return issues
