"""Hitta felet: a booked verifikation with one planted error, corrected by the learner.

The error is chosen by seed among those that fit the verifikation:
debet and kredit swapped on every row, a wrong momskonto (utgående instead
of ingående moms or the reverse), or a wrong amount (two adjacent digits
swapped on the largest row, with the largest row on the other side adjusted
so the verifikation still balances, as a bokföringsprogram demands).

The learner answers with a rättelseverifikation. It is posted with core
after the wrong verifikation, pointing at it; the answer is right when the
huvudbok then shows the same balances as if the correct verifikation alone
had been booked. Both a full reversal plus a new entry and a correction of
the difference only are accepted.
"""

import random
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, replace
from enum import StrEnum

from ra.core.chart import Chart
from ra.core.ledger import Journal, PostingError, ledger, open_journal, post
from ra.core.money import Money
from ra.core.voucher import IssueCode, Side, Voucher, VoucherKey, VoucherLine
from ra.learning.grading import ErrorCode, Grade, classify

CORRECTION_TEXT = "Rättelse"
FALLBACK_DELTA = Money(9_000)  # 90 kr, when no digits can be swapped
WRONG_VAT_ROLE: Mapping[str, str] = {
    "ingaende": "utgaende_25",
    "ingaende_beraknad": "ingaende",
    "utgaende_25": "ingaende",
    "utgaende_12": "ingaende",
    "utgaende_6": "ingaende",
    "utgaende_omvand_25": "utgaende_25",
}


class ErrorKind(StrEnum):
    SWAPPED_SIDES = "omkastade_sidor"
    WRONG_VAT_ACCOUNT = "fel_momskonto"
    WRONG_AMOUNT = "fel_belopp"


@dataclass(frozen=True)
class PlantedError:
    """The correct verifikation and the booked one with one error."""

    kind: ErrorKind
    correct: Voucher
    booked: Voucher


def _other(side: Side) -> Side:
    return Side.KREDIT if side is Side.DEBET else Side.DEBET


def _swap_sides(voucher: Voucher) -> Voucher:
    return replace(voucher, lines=tuple(VoucherLine(ln.account, _other(ln.side), ln.amount)
                                        for ln in voucher.lines))


def _vat_target(chart: Chart, line: VoucherLine) -> int | None:
    role = chart[line.account].moms_role if line.account in chart else None
    target_role = WRONG_VAT_ROLE.get(role or "")
    targets = chart.by_moms_role(target_role) if target_role else ()
    return targets[0].number if targets else None


def _wrong_vat_account(chart: Chart, voucher: Voucher, rng: random.Random) -> Voucher | None:
    candidates = [i for i, ln in enumerate(voucher.lines) if _vat_target(chart, ln) is not None]
    if not candidates:
        return None
    index = rng.choice(candidates)
    line = voucher.lines[index]
    wrong = VoucherLine(_vat_target(chart, line) or line.account, line.side, line.amount)
    return replace(voucher, lines=voucher.lines[:index] + (wrong,) + voucher.lines[index + 1:])


def transpositions(amount: Money) -> list[Money]:
    """Amounts with two adjacent kronor digits swapped (a common typing error)."""
    kronor, ore = divmod(amount.ore, 100)
    digits = str(kronor)
    found = []
    for i in range(len(digits) - 1):
        if digits[i] != digits[i + 1] and not (i == 0 and digits[i + 1] == "0"):
            swapped = digits[:i] + digits[i + 1] + digits[i] + digits[i + 2:]
            found.append(Money(int(swapped) * 100 + ore))
    return found


def _wrong_amount(voucher: Voucher, rng: random.Random) -> Voucher:
    lines = list(voucher.lines)
    big = max(range(len(lines)), key=lambda i: lines[i].amount)
    partner = max((i for i in range(len(lines)) if lines[i].side is not lines[big].side),
                  key=lambda i: lines[i].amount)
    old = lines[big].amount
    room = old - lines[partner].amount  # the partner must stay positive
    options = [m for m in transpositions(old) if m > room]
    new = rng.choice(options) if options else old + FALLBACK_DELTA
    delta = new - old
    lines[big] = VoucherLine(lines[big].account, lines[big].side, new)
    lines[partner] = VoucherLine(lines[partner].account, lines[partner].side,
                                 lines[partner].amount + delta)
    return replace(voucher, lines=tuple(lines))


def plant(chart: Chart, correct: Voucher, seed: int) -> PlantedError:
    """Book ``correct`` with exactly one error chosen by ``seed``."""
    rng = random.Random(seed)
    options: list[tuple[ErrorKind, Voucher]] = [
        (ErrorKind.SWAPPED_SIDES, _swap_sides(correct)),
        (ErrorKind.WRONG_AMOUNT, _wrong_amount(correct, rng)),
    ]
    wrong_vat = _wrong_vat_account(chart, correct, rng)
    if wrong_vat is not None:
        options.append((ErrorKind.WRONG_VAT_ACCOUNT, wrong_vat))
    kind, booked = rng.choice(options)
    return PlantedError(kind, correct, booked)


def _closing(journal: Journal) -> dict[int, Money]:
    return {n: a.closing for n, a in ledger(journal).items() if a.closing.ore != 0}


def _positions(balances: Mapping[int, Money]) -> dict[tuple[int, Side], Money]:
    return {(n, Side.DEBET if m.ore > 0 else Side.KREDIT): Money(abs(m.ore))
            for n, m in balances.items()}


def suggested_correction(chart: Chart, planted: PlantedError) -> tuple[VoucherLine, ...]:
    """The smallest rättelse: the difference between the correct and the booked effect."""
    right = _closing(post(open_journal(chart), planted.correct))
    wrong = _closing(post(open_journal(chart), planted.booked))
    lines = []
    for account in sorted(set(right) | set(wrong)):
        diff = right.get(account, Money.zero()) - wrong.get(account, Money.zero())
        if diff.ore:
            lines.append(VoucherLine(account, Side.DEBET if diff.ore > 0 else Side.KREDIT,
                                     Money(abs(diff.ore))))
    return tuple(lines)


def grade_correction(chart: Chart, planted: PlantedError,
                     correction: Iterable[VoucherLine]) -> Grade:
    """Right when booked plus rättelse leaves the same balances as the correct verifikation."""
    journal = post(open_journal(chart), planted.booked)
    key = VoucherKey(planted.booked.series, 1)
    rattelse = Voucher(planted.booked.series, planted.booked.date, CORRECTION_TEXT,
                       tuple(correction), corrects=key)
    try:
        corrected = post(journal, rattelse)
    except PostingError as error:
        unbalanced = any(i.code is IssueCode.UNBALANCED for i in error.issues)
        return Grade(False, (ErrorCode.OBALANS,) if unbalanced else ())
    expected = _closing(post(open_journal(chart), planted.correct))
    given = _closing(corrected)
    if given == expected:
        return Grade(True)
    return Grade(False, tuple(classify(chart, _positions(given), _positions(expected), {})))
