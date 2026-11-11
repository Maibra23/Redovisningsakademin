"""Tests for the accounting engine in ra.core."""

import datetime as dt

import pytest

from ra.core.formatting import NBSP, format_ore
from ra.core.money import Money, MoneyTypeError
from ra.core.voucher import IssueCode, Side, Voucher, VoucherLine, validate

# Neutral account numbers for engine tests; real BAS accounts come from content/kontoplan.yaml.
TEST_CHART = {1000, 2000, 3000}


def _voucher(*lines: tuple[int, Side, int]) -> Voucher:
    return Voucher(
        series="A",
        date=dt.date(2026, 1, 15),
        text="Test",
        lines=tuple(VoucherLine(acc, side, Money(ore)) for acc, side, ore in lines),
    )


def test_format_ore_swedish_amount() -> None:
    # 1 250 000 öre / 100 = 12 500 kr and 00 öre; thousands grouped with a (non-breaking) space.
    assert format_ore(1_250_000) == f"12{NBSP}500,00{NBSP}kr"


def test_percent_rounds_half_ore_up() -> None:
    # 10 öre * 25 / 100 = 2,5 öre -> 3 öre; 9 öre * 25 / 100 = 2,25 öre -> 2 öre.
    assert Money(10).percent(25) == Money(3)
    assert Money(9).percent(25) == Money(2)


def test_parse_swedish_text() -> None:
    # "1 250,50" = 1 250 kr * 100 + 50 öre = 125 050 öre; "1250,5" = 125 000 + 50 = 125 050.
    assert Money.parse("1 250,50") == Money(125_050)
    assert Money.parse("1250,5") == Money(125_050)


def test_float_is_rejected() -> None:
    with pytest.raises(MoneyTypeError):
        Money(12.5)  # type: ignore[arg-type]


def test_unbalanced_voucher_is_reported() -> None:
    # Debet 1 000,00 kr against kredit 900,00 kr: difference 100,00 kr.
    voucher = _voucher((1000, Side.DEBET, 100_000), (3000, Side.KREDIT, 90_000))
    assert [issue.code for issue in validate(TEST_CHART, voucher)] == [IssueCode.UNBALANCED]


def test_valid_voucher_has_no_issues() -> None:
    # Debet 1 250,00 = kredit 1 000,00 + 250,00.
    voucher = _voucher(
        (1000, Side.DEBET, 125_000), (3000, Side.KREDIT, 100_000), (2000, Side.KREDIT, 25_000)
    )
    assert validate(TEST_CHART, voucher) == []
