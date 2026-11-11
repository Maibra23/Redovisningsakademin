"""Grundbok (journal), huvudbok (ledger) and råbalans (trial balance).

The journal is append only: posting returns a new journal and never changes an
earlier verifikation. A mistake is fixed with a new rättelseverifikation that
points at the one it corrects. Balances are signed with debet as positive.
"""

from collections.abc import Mapping
from dataclasses import dataclass, field, replace
from types import MappingProxyType

from ra.core.chart import Chart
from ra.core.money import Money, total
from ra.core.voucher import Issue, Side, Voucher, VoucherKey, validate


class PostingError(ValueError):
    """A verifikation or an opening balance cannot be accepted."""

    def __init__(self, message: str, issues: tuple[Issue, ...] = ()) -> None:
        super().__init__(message)
        self.issues = issues


@dataclass(frozen=True)
class Journal:
    """Ingående balanser (signed, debet positive) and posted verifikationer in order."""

    chart: Chart
    opening: Mapping[int, Money] = field(default_factory=dict)
    vouchers: tuple[Voucher, ...] = ()

    def find(self, key: VoucherKey) -> Voucher | None:
        return next((v for v in self.vouchers if v.number == key.number
                     and v.series == key.series), None)


def open_journal(chart: Chart, opening: Mapping[int, Money] | None = None) -> Journal:
    """New journal with ingående balanser that must balance to zero."""
    balances = dict(opening or {})
    unknown = sorted(n for n in balances if n not in chart)
    if unknown:
        raise PostingError(f"Opening balance on unknown accounts: {unknown}")
    if total(list(balances.values())) != Money.zero():
        raise PostingError("Opening balances do not balance: debet must equal kredit")
    return Journal(chart=chart, opening=MappingProxyType(balances))


def _next_number(journal: Journal, series: str) -> int:
    numbers = [v.number for v in journal.vouchers if v.series == series and v.number]
    return max(numbers, default=0) + 1


def post(journal: Journal, voucher: Voucher) -> Journal:
    """Bokför: validate, give the next number in the series and append.

    A rättelse must point at a verifikation that is already in the journal.
    """
    issues = tuple(validate(journal.chart, voucher))
    if issues:
        raise PostingError("Verifikation is not valid", issues)
    if voucher.number is not None:
        raise PostingError("The journal assigns the number; leave it empty")
    if voucher.corrects is not None and journal.find(voucher.corrects) is None:
        raise PostingError(f"Corrected verifikation {voucher.corrects} does not exist")
    numbered = replace(voucher, number=_next_number(journal, voucher.series))
    return replace(journal, vouchers=journal.vouchers + (numbered,))


@dataclass(frozen=True)
class LedgerAccount:
    """One konto in the huvudbok: ingående balans, rörelser and utgående balans."""

    number: int
    opening: Money
    debet: Money
    kredit: Money

    @property
    def closing(self) -> Money:
        return self.opening + self.debet - self.kredit


def ledger(journal: Journal) -> dict[int, LedgerAccount]:
    """Huvudbok for every account with an opening balance or a movement."""
    debet: dict[int, list[Money]] = {}
    kredit: dict[int, list[Money]] = {}
    for voucher in journal.vouchers:
        for line in voucher.lines:
            target = debet if line.side is Side.DEBET else kredit
            target.setdefault(line.account, []).append(line.amount)
    numbers = sorted(set(journal.opening) | set(debet) | set(kredit))
    return {
        n: LedgerAccount(
            number=n,
            opening=journal.opening.get(n, Money.zero()),
            debet=total(debet.get(n, [])),
            kredit=total(kredit.get(n, [])),
        )
        for n in numbers
    }


@dataclass(frozen=True)
class TrialBalance:
    """Råbalans: every account's utgående balans in a debet or kredit column."""

    accounts: tuple[LedgerAccount, ...]
    total_debet: Money
    total_kredit: Money

    @property
    def balances(self) -> bool:
        return self.total_debet == self.total_kredit


def trial_balance(journal: Journal) -> TrialBalance:
    """Summa debet and summa kredit of the utgående balanser; they must be equal."""
    accounts = tuple(ledger(journal).values())
    closings = [a.closing for a in accounts]
    return TrialBalance(
        accounts=accounts,
        total_debet=total([c for c in closings if c.ore > 0]),
        total_kredit=-total([c for c in closings if c.ore < 0]),
    )
