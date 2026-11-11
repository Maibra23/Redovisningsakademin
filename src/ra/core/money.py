"""Money as integer öre (belopp i hela ören).

Every amount in the app is an integer number of öre. Floats are refused at
construction, because binary floating point cannot hold most öre amounts
exactly. Percentages are computed with Decimal and rounded half up to whole
öre (avrundning till närmaste öre, halvt öre uppåt).
"""

import re
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

ORE_PER_KRONA = 100

# "1 250,50", "1250,5", "-75", "12 500,00 kr"; spaces may be normal or non-breaking.
_SWEDISH_AMOUNT = re.compile(
    r"^(?P<sign>-)?(?P<kronor>\d{1,3}(?: \d{3})+|\d+)(?:,(?P<ore>\d{1,2}))?(?: ?kr)?$"
)


class MoneyTypeError(TypeError):
    """An amount was built from something other than integer öre."""


class MoneyParseError(ValueError):
    """Text could not be read as a Swedish amount."""


@dataclass(frozen=True, order=True)
class Money:
    """An amount in öre (belopp). ``Money(125050)`` is 1 250,50 kr."""

    ore: int

    def __post_init__(self) -> None:
        if isinstance(self.ore, bool) or not isinstance(self.ore, int):
            raise MoneyTypeError(f"Money needs integer öre, got {type(self.ore).__name__}")

    @classmethod
    def zero(cls) -> "Money":
        return cls(0)

    @classmethod
    def parse(cls, text: str) -> "Money":
        """Read a Swedish amount: space as thousands separator, comma as decimal sign."""
        cleaned = text.replace(" ", " ").strip()
        match = _SWEDISH_AMOUNT.fullmatch(cleaned)
        if match is None:
            raise MoneyParseError(f"Not a Swedish amount: {text!r}")
        kronor = int(match["kronor"].replace(" ", ""))
        ore = int((match["ore"] or "0").ljust(2, "0"))
        total = kronor * ORE_PER_KRONA + ore
        return cls(-total if match["sign"] else total)

    def __add__(self, other: "Money") -> "Money":
        if not isinstance(other, Money):
            return NotImplemented
        return Money(self.ore + other.ore)

    def __sub__(self, other: "Money") -> "Money":
        if not isinstance(other, Money):
            return NotImplemented
        return Money(self.ore - other.ore)

    def __neg__(self) -> "Money":
        return Money(-self.ore)

    def percent(self, rate: Decimal | int | str) -> "Money":
        """``rate`` percent of this amount, rounded half up to whole öre.

        Procentberäkning: 25 procent of 10 öre is 2,5 öre, which rounds to 3 öre.
        Halves round away from zero, so negative amounts mirror positive ones.
        ``rate`` is given in percent (25 means 25 procent) and must not be a float.
        """
        if isinstance(rate, float):
            raise MoneyTypeError("Percent rate must be Decimal, int or str, not float")
        exact = Decimal(self.ore) * Decimal(rate) / Decimal(100)
        return Money(int(exact.quantize(Decimal(1), rounding=ROUND_HALF_UP)))


def total(amounts: "list[Money] | tuple[Money, ...]") -> Money:
    """Sum of amounts (summa); zero for an empty list."""
    result = Money.zero()
    for amount in amounts:
        result = result + amount
    return result
