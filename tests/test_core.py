"""Tests for the accounting engine in ra.core."""

from ra.core.formatting import NBSP, format_ore


def test_format_ore_swedish_amount() -> None:
    # 1 250 000 öre / 100 = 12 500 kr and 00 öre; thousands grouped with a (non-breaking) space.
    assert format_ore(1_250_000) == f"12{NBSP}500,00{NBSP}kr"
