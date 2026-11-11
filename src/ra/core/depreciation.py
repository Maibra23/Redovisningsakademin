"""Avskrivning (depreciation) with a straight line plan (linjär avskrivning).

The cost (anskaffningsvärde) is spread evenly over the months of the useful
life. Each month gets the cost divided by the number of months, rounded down
to whole öre; the last month takes the rounding remainder so the plan sums
exactly to the cost.
"""

import datetime as dt

from ra.core.money import Money
from ra.core.voucher import Side, Voucher, VoucherLine

DEPRECIATION_TEXT = "Avskrivning inventarier"
EXPENSE_ACCOUNT = 7832  # Avskrivningar på inventarier, verktyg och installationer
ACCUMULATED_ACCOUNT = 1229  # Ackumulerade avskrivningar på inventarier, verktyg och installationer


class DepreciationError(ValueError):
    """The depreciation plan input is not valid."""


def monthly(cost: Money, months: int) -> tuple[Money, ...]:
    """Avskrivningsplan: one amount per month, summing exactly to ``cost``."""
    if months < 1:
        raise DepreciationError("The plan needs at least one month")
    if cost.ore <= 0:
        raise DepreciationError("Anskaffningsvärde must be positive")
    base = Money(cost.ore // months)
    last = cost - Money(base.ore * (months - 1))
    return (base,) * (months - 1) + (last,)


def voucher(
    amount: Money,
    on_date: dt.date,
    series: str = "A",
    expense_account: int = EXPENSE_ACCOUNT,
    accumulated_account: int = ACCUMULATED_ACCOUNT,
) -> Voucher:
    """Monthly avskrivning: debet avskrivningskostnad, kredit ackumulerade avskrivningar."""
    return Voucher(
        series=series,
        date=on_date,
        text=DEPRECIATION_TEXT,
        lines=(
            VoucherLine(expense_account, Side.DEBET, amount),
            VoucherLine(accumulated_account, Side.KREDIT, amount),
        ),
    )
