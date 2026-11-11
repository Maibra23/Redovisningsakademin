"""Resultaträkning (income statement) and balansräkning (balance sheet).

Every account belongs to one report line through its ``report_line`` in the
kontoplan. Line names follow the kostnadsslagsindelad resultaträkning in
K2 (BFNAR 2016:10, punkt 4.4) and the balansräkning in årsredovisningslagen
(1995:1554) bilaga 1. The resultaträkning uses the period's movements; the
balansräkning uses utgående balanser. Before the bokslut the period's result
still sits in the result accounts, so it is added to Årets resultat in eget
kapital; then summa tillgångar equals summa eget kapital och skulder.
"""

from dataclasses import dataclass

from ra.core.chart import Chart
from ra.core.ledger import Journal, ledger
from ra.core.money import Money, total

# (report line code, label). Amounts: intäkter positive, kostnader negative.
OPERATING_LINES: tuple[tuple[str, str], ...] = (
    ("rr.nettoomsattning", "Nettoomsättning"),
    ("rr.ravaror_fornodenheter", "Råvaror och förnödenheter"),
    ("rr.handelsvaror", "Handelsvaror"),
    ("rr.ovriga_externa_kostnader", "Övriga externa kostnader"),
    ("rr.personalkostnader", "Personalkostnader"),
    ("rr.avskrivningar",
     "Av- och nedskrivningar av materiella och immateriella anläggningstillgångar"),
)
FINANCIAL_LINES: tuple[tuple[str, str], ...] = (
    ("rr.ranteintakter", "Övriga ränteintäkter och liknande resultatposter"),
    ("rr.rantekostnader", "Räntekostnader och liknande resultatposter"),
)
TAX_LINES: tuple[tuple[str, str], ...] = (("rr.skatt", "Skatt på årets resultat"),)

ASSET_LINES: tuple[tuple[str, str], ...] = (
    ("br.inventarier", "Inventarier, verktyg och installationer"),
    ("br.varulager", "Färdiga varor och handelsvaror"),
    ("br.kundfordringar", "Kundfordringar"),
    ("br.ovriga_fordringar", "Övriga fordringar"),
    ("br.forutbetalda_upplupna", "Förutbetalda kostnader och upplupna intäkter"),
    ("br.kassa_bank", "Kassa och bank"),
)
EQUITY_LIABILITY_LINES: tuple[tuple[str, str], ...] = (
    ("br.aktiekapital", "Aktiekapital"),
    ("br.balanserat_resultat", "Balanserad vinst eller förlust"),
    ("br.arets_resultat", "Årets resultat"),
    ("br.langfristiga_skulder", "Skulder till kreditinstitut"),
    ("br.leverantorsskulder", "Leverantörsskulder"),
    ("br.skatteskulder", "Skatteskulder"),
    ("br.ovriga_kortfristiga_skulder", "Övriga skulder"),
    ("br.upplupna_forutbetalda", "Upplupna kostnader och förutbetalda intäkter"),
)
RESULT_LINE = "br.arets_resultat"


class ReportError(ValueError):
    """An account has a report line the reports do not know."""


@dataclass(frozen=True)
class ReportLine:
    code: str
    label: str
    amount: Money


@dataclass(frozen=True)
class IncomeStatement:
    """Resultaträkning: rörelseresultat, resultat efter finansiella poster, årets resultat."""

    operating: tuple[ReportLine, ...]
    financial: tuple[ReportLine, ...]
    tax: tuple[ReportLine, ...]

    @property
    def operating_result(self) -> Money:
        """Rörelseresultat."""
        return total([line.amount for line in self.operating])

    @property
    def result_after_financial_items(self) -> Money:
        """Resultat efter finansiella poster."""
        return self.operating_result + total([line.amount for line in self.financial])

    @property
    def net_result(self) -> Money:
        """Årets resultat (here: the period's result)."""
        return self.result_after_financial_items + total([line.amount for line in self.tax])


@dataclass(frozen=True)
class BalanceSheet:
    """Balansräkning with summa tillgångar and summa eget kapital och skulder."""

    assets: tuple[ReportLine, ...]
    equity_and_liabilities: tuple[ReportLine, ...]

    @property
    def total_assets(self) -> Money:
        return total([line.amount for line in self.assets])

    @property
    def total_equity_and_liabilities(self) -> Money:
        return total([line.amount for line in self.equity_and_liabilities])


def _check_lines(chart: Chart) -> None:
    known = {code for group in (OPERATING_LINES, FINANCIAL_LINES, TAX_LINES, ASSET_LINES,
                                EQUITY_LIABILITY_LINES) for code, _ in group}
    unknown = sorted({chart[n].report_line for n in chart} - known)
    if unknown:
        raise ReportError(f"Report lines without a place in the reports: {unknown}")


def _sum_by_line(chart: Chart, amounts: dict[int, Money]) -> dict[str, Money]:
    by_line: dict[str, list[Money]] = {}
    for number, amount in amounts.items():
        by_line.setdefault(chart[number].report_line, []).append(amount)
    return {code: total(values) for code, values in by_line.items()}


def _lines(spec: tuple[tuple[str, str], ...], sums: dict[str, Money],
           sign: int) -> tuple[ReportLine, ...]:
    zero = Money(0)
    return tuple(ReportLine(code, label, sums.get(code, zero) if sign > 0
                            else -sums.get(code, zero)) for code, label in spec)


def income_statement(chart: Chart, journal: Journal) -> IncomeStatement:
    """Resultaträkning from the period's movements (kredit minus debet per line)."""
    _check_lines(chart)
    movements = {n: a.kredit - a.debet for n, a in ledger(journal).items()
                 if chart[n].report_line.startswith("rr.")}
    sums = _sum_by_line(chart, movements)
    return IncomeStatement(
        operating=_lines(OPERATING_LINES, sums, 1),
        financial=_lines(FINANCIAL_LINES, sums, 1),
        tax=_lines(TAX_LINES, sums, 1),
    )


def balance_sheet(chart: Chart, journal: Journal) -> BalanceSheet:
    """Balansräkning from utgående balanser, with the period's result in Årets resultat."""
    _check_lines(chart)
    closing = {n: a.closing for n, a in ledger(journal).items()
               if chart[n].report_line.startswith("br.")}
    sums = _sum_by_line(chart, closing)
    result = income_statement(chart, journal).net_result
    sums[RESULT_LINE] = sums.get(RESULT_LINE, Money(0)) - result
    return BalanceSheet(
        assets=_lines(ASSET_LINES, sums, 1),
        equity_and_liabilities=_lines(EQUITY_LIABILITY_LINES, sums, -1),
    )
