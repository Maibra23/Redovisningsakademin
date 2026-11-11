"""Moms (Swedish VAT): rates by date, calculation, report and settlement.

Rates are data in ``content/momssatser.yaml``, looked up by code and the date
of the transaction. Utgående moms is moms on sales, ingående moms is moms on
purchases that the company may deduct. The period's net is utgående minus
ingående moms; the settlement (momsomföring) moves it to the
momsredovisningskonto.
"""

import datetime as dt
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path
from typing import Any

import yaml

from ra.core.chart import Chart
from ra.core.ledger import Journal
from ra.core.money import Money, total
from ra.core.voucher import Side, Voucher, VoucherLine

OUTPUT_ROLES: dict[str, int] = {"utgaende_25": 25, "utgaende_12": 12, "utgaende_6": 6}
INPUT_ROLE = "ingaende"
SETTLEMENT_ROLE = "momsredovisning"
SETTLEMENT_TEXT = "Omföring av moms"


class VatError(ValueError):
    """A moms rate is missing, overlapping or not valid."""


@dataclass(frozen=True)
class VatRate:
    """One momssats for a code during a date range (both ends inclusive)."""

    code: str
    rate: Fraction
    valid_from: dt.date | None
    valid_to: dt.date | None
    source: str
    checked_on: dt.date

    def covers(self, on_date: dt.date) -> bool:
        after_start = self.valid_from is None or on_date >= self.valid_from
        before_end = self.valid_to is None or on_date <= self.valid_to
        return after_start and before_end


@dataclass(frozen=True)
class VatAmounts:
    """Nettobelopp, moms and bruttobelopp for one amount."""

    net: Money
    vat: Money
    gross: Money


class VatTable:
    """All momssatser, looked up by code and date."""

    def __init__(self, rates: tuple[VatRate, ...]) -> None:
        _check_no_overlap(rates)
        self._rates = rates

    def rate_for(self, code: str, on_date: dt.date) -> Fraction:
        """Momssats in percent for ``code`` on ``on_date``."""
        matches = [r for r in self._rates if r.code == code and r.covers(on_date)]
        if not matches:
            raise VatError(f"No moms rate for {code} on {on_date.isoformat()}")
        return matches[0].rate

    def add(self, net: Money, code: str, on_date: dt.date) -> VatAmounts:
        """Moms on a net amount: moms = netto x sats, rounded half up to whole öre."""
        vat = net.percent(self.rate_for(code, on_date))
        return VatAmounts(net=net, vat=vat, gross=net + vat)

    def split(self, gross: Money, code: str, on_date: dt.date) -> VatAmounts:
        """Moms inside a gross amount: moms = brutto x sats / (100 + sats).

        At 25 procent the moms is 20 procent of the gross amount.
        """
        rate = self.rate_for(code, on_date)
        vat = gross.percent(rate * 100 / (100 + rate))
        return VatAmounts(net=gross - vat, vat=vat, gross=gross)


def _check_no_overlap(rates: tuple[VatRate, ...]) -> None:
    by_code: dict[str, list[VatRate]] = {}
    for rate in rates:
        by_code.setdefault(rate.code, []).append(rate)
    for code, entries in by_code.items():
        ordered = sorted(entries, key=lambda r: r.valid_from or dt.date.min)
        for earlier, later in zip(ordered, ordered[1:], strict=False):
            end = earlier.valid_to or dt.date.max
            start = later.valid_from or dt.date.min
            if start <= end:
                raise VatError(f"Overlapping moms rates for {code}")


def _parse_rate(raw: dict[str, Any]) -> VatRate:
    try:
        return VatRate(
            code=str(raw["code"]),
            rate=Fraction(str(raw["rate"])),
            valid_from=raw.get("valid_from"),
            valid_to=raw.get("valid_to"),
            source=str(raw["source"]),
            checked_on=raw["checked_on"],
        )
    except (KeyError, ValueError, TypeError) as error:
        raise VatError(f"Invalid moms rate entry {raw!r}: {error}") from error


def load_vat_table(path: Path) -> VatTable:
    """Load ``content/momssatser.yaml``."""
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not isinstance(data.get("rates"), list):
        raise VatError(f"{path}: expected a mapping with a 'rates' list")
    return VatTable(tuple(_parse_rate(raw) for raw in data["rates"]))


@dataclass(frozen=True)
class VatReport:
    """Momsrapport for a period: utgående moms per rate, ingående moms and the net.

    A positive net is moms to pay (moms att betala); a negative net is moms
    to get back (moms att få tillbaka).
    """

    output_by_rate: dict[int, Money]
    input_vat: Money

    @property
    def output_total(self) -> Money:
        return total(list(self.output_by_rate.values()))

    @property
    def net(self) -> Money:
        return self.output_total - self.input_vat


def _period_vouchers(chart: Chart, journal: Journal) -> tuple[Voucher, ...]:
    """Verifikationer of the period, leaving out earlier momsomföringar."""
    settlement_accounts = {a.number for a in chart.by_moms_role(SETTLEMENT_ROLE)}
    return tuple(
        v for v in journal.vouchers
        if not any(line.account in settlement_accounts for line in v.lines)
    )


def _movement(vouchers: tuple[Voucher, ...], account: int, side: Side) -> Money:
    """Net movement on ``account``, positive when it moves on ``side``."""
    signed = [
        line.amount if line.side is side else -line.amount
        for v in vouchers for line in v.lines if line.account == account
    ]
    return total(signed)


def report(chart: Chart, journal: Journal) -> VatReport:
    """Utgående moms per rate (kredit movement), ingående moms (debet movement), net."""
    vouchers = _period_vouchers(chart, journal)
    output_by_rate = {
        rate: total([_movement(vouchers, a.number, Side.KREDIT) for a in chart.by_moms_role(role)])
        for role, rate in OUTPUT_ROLES.items()
    }
    input_vat = total([_movement(vouchers, a.number, Side.DEBET)
                       for a in chart.by_moms_role(INPUT_ROLE)])
    return VatReport(output_by_rate=output_by_rate, input_vat=input_vat)


def settlement(chart: Chart, journal: Journal, on_date: dt.date, series: str = "A") -> Voucher:
    """Momsomföring: clear the moms accounts and put the net on the momsredovisningskonto.

    Each utgående account is debited and each ingående account credited by its
    movement in the period; the net goes to kredit (to pay) or debet (to get back).
    The verifikation is returned unposted; post it with ``ledger.post``.
    """
    vouchers = _period_vouchers(chart, journal)
    lines: list[VoucherLine] = []
    for role in OUTPUT_ROLES:
        for account in chart.by_moms_role(role):
            lines += _clearing_line(account.number, _movement(vouchers, account.number,
                                                              Side.KREDIT), Side.DEBET)
    for account in chart.by_moms_role(INPUT_ROLE):
        lines += _clearing_line(account.number, _movement(vouchers, account.number, Side.DEBET),
                                Side.KREDIT)
    net = report(chart, journal).net
    settlement_account = chart.by_moms_role(SETTLEMENT_ROLE)[0].number
    lines += _clearing_line(settlement_account, net, Side.KREDIT)
    return Voucher(series=series, date=on_date, text=SETTLEMENT_TEXT, lines=tuple(lines))


def _clearing_line(account: int, amount: Money, side: Side) -> list[VoucherLine]:
    """A line of ``amount`` on ``side``; a negative amount goes on the other side."""
    if amount.ore == 0:
        return []
    other = Side.KREDIT if side is Side.DEBET else Side.DEBET
    return [VoucherLine(account, side if amount.ore > 0 else other,
                        amount if amount.ore > 0 else -amount)]
