"""Grading: decide right or wrong and classify the error (rättning).

Kontering: rows on the same account and side are merged, row order is
ignored, declared alternative accounts are accepted and amounts must agree
to the öre. A wrong kontering is compared with the accepted solution and
classified into the error codes of architecture section 8, most telling
code first. Beräkning compares one amount exactly, klassificering compares
sets of (item, category) and resonemang compares the chosen alternative.
"""

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from enum import StrEnum

from ra.core.chart import Chart
from ra.core.money import Money, total
from ra.core.voucher import Side, VoucherLine
from ra.learning.recipes import RecipeResult


class ErrorCode(StrEnum):
    OBALANS = "OBALANS"
    FEL_SIDA = "FEL_SIDA"
    FEL_KONTO = "FEL_KONTO"
    FEL_KONTOKLASS = "FEL_KONTOKLASS"
    MOMS_SAKNAS = "MOMS_SAKNAS"
    MOMS_FEL_SATS = "MOMS_FEL_SATS"
    MOMS_PA_BRUTTO = "MOMS_PA_BRUTTO"
    MOMS_FEL_RIKTNING = "MOMS_FEL_RIKTNING"
    FEL_BELOPP = "FEL_BELOPP"
    RAD_SAKNAS = "RAD_SAKNAS"
    EXTRA_RAD = "EXTRA_RAD"


# The first code in this order is the one the feedback is worded around.
PRIORITY: tuple[ErrorCode, ...] = (
    ErrorCode.FEL_SIDA, ErrorCode.MOMS_PA_BRUTTO, ErrorCode.MOMS_FEL_RIKTNING,
    ErrorCode.MOMS_FEL_SATS, ErrorCode.MOMS_SAKNAS, ErrorCode.FEL_KONTOKLASS,
    ErrorCode.FEL_KONTO, ErrorCode.OBALANS, ErrorCode.FEL_BELOPP, ErrorCode.RAD_SAKNAS,
    ErrorCode.EXTRA_RAD,
)
SALE_RATES = (25, 12, 6)
OUTPUT_PREFIX = "utgaende"
INPUT_ROLES = frozenset({"ingaende", "ingaende_beraknad"})

Position = tuple[int, Side]


@dataclass(frozen=True)
class Grade:
    """Result of grading one answer; ``codes`` is empty when correct or unclassified."""

    correct: bool
    codes: tuple[ErrorCode, ...] = ()

    @property
    def primary(self) -> ErrorCode | None:
        return self.codes[0] if self.codes else None


def _other(side: Side) -> Side:
    return Side.KREDIT if side is Side.DEBET else Side.DEBET


def merge(lines: Iterable[VoucherLine]) -> dict[Position, Money]:
    """Sum rows with the same account and side; rows with a zero amount are dropped."""
    merged: dict[Position, Money] = {}
    for line in lines:
        if line.amount.ore != 0:
            position = (line.account, line.side)
            merged[position] = merged.get(position, Money.zero()) + line.amount
    return merged


def _apply_alternatives(answer: dict[Position, Money], key: Mapping[Position, Money],
                        alternatives: Mapping[int, frozenset[int]]) -> dict[Position, Money]:
    """Read an accepted alternative account as the key's account."""
    key_accounts = {account for account, _ in key}
    renamed: dict[Position, Money] = {}
    for (account, side), amount in answer.items():
        target = next((k for k, accepted in alternatives.items()
                       if account in accepted and k in key_accounts
                       and account not in key_accounts), account)
        position = (target, side)
        renamed[position] = renamed.get(position, Money.zero()) + amount
    return renamed


def _moms_direction(chart: Chart, account: int) -> str | None:
    role = chart[account].moms_role if account in chart else None
    if role is None:
        return None
    if role.startswith(OUTPUT_PREFIX):
        return "ut"
    return "in" if role in INPUT_ROLES else None


def _moms_rate(chart: Chart, account: int) -> str | None:
    return chart[account].moms_role if account in chart else None


def _figure(figures: Mapping[str, object], key: str) -> Money | None:
    value = figures.get(key)
    return value if isinstance(value, Money) else None


def _moms_amount_code(amount: Money, figures: Mapping[str, object]) -> ErrorCode:
    """Why a moms row has the wrong amount: computed on the gross, at another rate, or other."""
    gross, net = _figure(figures, "brutto"), _figure(figures, "netto")
    rate = figures.get("momssats")
    if gross is not None and isinstance(rate, int) and amount == gross.percent(rate):
        return ErrorCode.MOMS_PA_BRUTTO
    if net is not None and any(amount == net.percent(r) for r in SALE_RATES if r != rate):
        return ErrorCode.MOMS_FEL_SATS
    return ErrorCode.FEL_BELOPP


def _account_code(chart: Chart, key_account: int, answer_account: int) -> ErrorCode:
    key_dir = _moms_direction(chart, key_account)
    answer_dir = _moms_direction(chart, answer_account)
    if key_dir and answer_dir:
        if key_dir != answer_dir:
            return ErrorCode.MOMS_FEL_RIKTNING
        if _moms_rate(chart, key_account) != _moms_rate(chart, answer_account):
            return ErrorCode.MOMS_FEL_SATS
    if answer_account not in chart or chart[answer_account].kind != chart[key_account].kind:
        return ErrorCode.FEL_KONTOKLASS
    return ErrorCode.FEL_KONTO


def _take(rows: dict[Position, Money], position: Position) -> Money:
    return rows.pop(position)


def classify(chart: Chart, answer: Mapping[Position, Money], key: Mapping[Position, Money],
             figures: Mapping[str, object]) -> list[ErrorCode]:
    """Error codes for a kontering that differs from ``key``, most telling first."""
    a, k = dict(answer), dict(key)
    codes: list[ErrorCode] = []
    debet = total([m for (_, side), m in a.items() if side is Side.DEBET])
    kredit = total([m for (_, side), m in a.items() if side is Side.KREDIT])
    if debet != kredit:
        codes.append(ErrorCode.OBALANS)
    for position in [p for p in k if a.get(p) == k[p]]:
        _take(a, position)
        _take(k, position)
    for account, side in [p for p in k if (p[0], _other(p[1])) in a]:
        _take(a, (account, _other(side)))
        _take(k, (account, side))
        codes.append(ErrorCode.FEL_SIDA)
    for position in [p for p in k if p in a]:
        amount = _take(a, position)
        _take(k, position)
        is_moms = _moms_direction(chart, position[0]) is not None
        codes.append(_moms_amount_code(amount, figures) if is_moms else ErrorCode.FEL_BELOPP)
    codes += _pair_remaining(chart, a, k, figures)
    codes += [ErrorCode.MOMS_SAKNAS if _moms_direction(chart, acc) else ErrorCode.RAD_SAKNAS
              for acc, _ in k]
    codes += [ErrorCode.EXTRA_RAD for _ in a]
    return sorted(set(codes), key=PRIORITY.index)


def _pair_remaining(chart: Chart, a: dict[Position, Money], k: dict[Position, Money],
                    figures: Mapping[str, object]) -> list[ErrorCode]:
    """Pair leftover rows that stand in for each other: moms with moms, then by side and amount."""
    codes: list[ErrorCode] = []
    for key_pos in [p for p in k if _moms_direction(chart, p[0])]:
        candidates = [p for p in a if _moms_direction(chart, p[0])]
        if candidates:
            answer_pos = min(candidates, key=lambda p: p[1] is not key_pos[1])
            amount, expected = _take(a, answer_pos), _take(k, key_pos)
            codes.append(_account_code(chart, key_pos[0], answer_pos[0]))
            if amount != expected:
                codes.append(_moms_amount_code(amount, figures))
    for key_pos in list(k):
        same_side = [p for p in a if p[1] is key_pos[1]]
        if not same_side:
            continue
        answer_pos = min(same_side, key=lambda p: a[p] != k[key_pos])
        amount, expected = _take(a, answer_pos), _take(k, key_pos)
        codes.append(_account_code(chart, key_pos[0], answer_pos[0]))
        if amount != expected:
            codes.append(ErrorCode.FEL_BELOPP)
    return codes


def grade_kontering(chart: Chart, answer: Iterable[VoucherLine], key: RecipeResult) -> Grade:
    """Kontering: merged rows, any order, accepted alternatives, exact öre."""
    expected = merge(key.voucher.lines)
    given = _apply_alternatives(merge(answer), expected, key.alternatives)
    if given == expected:
        return Grade(correct=True)
    return Grade(correct=False, codes=tuple(classify(chart, given, expected, key.figures)))


def grade_amount(answer: Money, expected: Money, figures: Mapping[str, object],
                 figure_name: str) -> Grade:
    """Beräkning: exact öre. Moms computed on the gross amount is recognised."""
    if answer == expected:
        return Grade(correct=True)
    code = _moms_amount_code(answer, figures) if figure_name == "moms" else ErrorCode.FEL_BELOPP
    return Grade(correct=False, codes=(code,))


def grade_classification(answer: Mapping[str, str], expected: Mapping[str, str]) -> Grade:
    """Klassificering: the set of (item, category) pairs must be equal."""
    return Grade(correct=set(answer.items()) == set(expected.items()))


def grade_choice(answer: int | None, expected: int) -> Grade:
    """Resonemang: the chosen alternative."""
    return Grade(correct=answer == expected)
