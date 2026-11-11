"""Tests for the accounting engine in ra.core."""

import datetime as dt
from pathlib import Path

import pytest

from ra.core.chart import Chart, load_chart
from ra.core.formatting import NBSP, format_ore
from ra.core.ledger import ledger, open_journal, post, trial_balance
from ra.core.money import Money, MoneyTypeError
from ra.core.vat import (
    VatTable,
    eu_purchase_lines,
    eu_sale_lines,
    load_vat_table,
    report,
    settlement,
)
from ra.core.voucher import IssueCode, Side, Voucher, VoucherKey, VoucherLine, validate

CONTENT = Path(__file__).resolve().parents[1] / "content"
KONTOPLAN = CONTENT / "kontoplan.yaml"
D, K = Side.DEBET, Side.KREDIT

# Neutral account numbers for engine tests; real BAS accounts come from content/kontoplan.yaml.
TEST_CHART = {1000, 2000, 3000}


def _voucher(
    *lines: tuple[int, Side, int], text: str = "Test", corrects: VoucherKey | None = None
) -> Voucher:
    return Voucher(
        series="A",
        date=dt.date(2026, 1, 15),
        text=text,
        lines=tuple(VoucherLine(acc, side, Money(ore)) for acc, side, ore in lines),
        corrects=corrects,
    )


@pytest.fixture(scope="module")
def chart() -> Chart:
    return load_chart(KONTOPLAN)


@pytest.fixture(scope="module")
def vat_table() -> VatTable:
    return load_vat_table(CONTENT / "momssatser.yaml")


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


def test_journal_trial_balance_and_correction(chart: Chart) -> None:
    # Ingående balans: 1930 D 100 000; 2081 K 50 000; 2091 K 50 000 (kronor).
    journal = open_journal(chart, {1930: Money(10_000_000), 2081: Money(-5_000_000),
                                   2091: Money(-5_000_000)})
    vouchers = [
        _voucher((1510, D, 1_250_000), (3001, K, 1_000_000), (2611, K, 250_000)),  # A1 sale
        _voucher((1930, D, 1_250_000), (1510, K, 1_250_000)),  # A2 customer pays
        _voucher((5010, D, 800_000), (1930, K, 800_000)),  # A3 rent
        _voucher((4010, D, 400_000), (2641, D, 100_000), (2440, K, 500_000)),  # A4 purchase
        _voucher((5460, D, 40_000), (1930, K, 40_000)),  # A5 kontorsmateriel on wrong account
    ]
    for voucher in vouchers:
        journal = post(journal, voucher)
    before = journal
    journal = post(journal, _voucher((6110, D, 40_000), (5460, K, 40_000), text="Rättelse A5",
                                     corrects=VoucherKey("A", 5)))
    # Utgående balanser (kronor):
    #   1930 = 100 000 + 12 500 - 8 000 - 400 = 104 100 D; 1510 = 12 500 - 12 500 = 0
    #   5010 8 000 D; 4010 4 000 D; 2641 1 000 D; 6110 400 D; 5460 = 400 - 400 = 0
    #   2081 50 000 K; 2091 50 000 K; 3001 10 000 K; 2611 2 500 K; 2440 5 000 K
    # Summa debet  = 104 100 + 8 000 + 4 000 + 1 000 + 400 = 117 500
    # Summa kredit = 50 000 + 50 000 + 10 000 + 2 500 + 5 000 = 117 500
    result = trial_balance(journal)
    assert result.total_debet == result.total_kredit == Money(11_750_000)
    assert journal.vouchers[:5] == before.vouchers
    assert [v.number for v in journal.vouchers] == [1, 2, 3, 4, 5, 6]
    assert journal.vouchers[4].lines[0].account == 5460


@pytest.mark.parametrize(
    ("code", "vat_ore"),
    # Net 1 000,00 kr = 100 000 öre: 25 % -> 25 000, 12 % -> 12 000, 6 % -> 6 000 öre.
    [("moms_25", 25_000), ("moms_12", 12_000), ("moms_6", 6_000)],
)
def test_each_rate(vat_table: VatTable, code: str, vat_ore: int) -> None:
    amounts = vat_table.add(Money(100_000), code, dt.date(2026, 6, 1))
    assert amounts.vat == Money(vat_ore)
    assert amounts.gross == Money(100_000 + vat_ore)


def test_livsmedel_rate_changes_on_1_april_2026(vat_table: VatTable) -> None:
    # Prop. 2025/26:55: 12 % up to 31 March 2026, 6 % from 1 April 2026.
    assert vat_table.rate_for("livsmedel", dt.date(2026, 3, 31)) == 12
    assert vat_table.rate_for("livsmedel", dt.date(2026, 4, 1)) == 6


def test_vat_report_net_equals_settlement(chart: Chart) -> None:
    journal = open_journal(chart)
    for voucher in (
        _voucher((1510, D, 1_250_000), (3001, K, 1_000_000), (2611, K, 250_000)),  # 25 % sale
        _voucher((1510, D, 112_000), (3002, K, 100_000), (2621, K, 12_000)),  # 12 % sale
        _voucher((4010, D, 400_000), (2641, D, 100_000), (2440, K, 500_000)),  # purchase
    ):
        journal = post(journal, voucher)
    # Utgående moms: 25 % 2 500,00 + 12 % 120,00 = 2 620,00; ingående moms 1 000,00.
    # Net to pay = 2 620,00 - 1 000,00 = 1 620,00 kr = 162 000 öre.
    vat = report(chart, journal)
    assert vat.output_by_rate == {25: Money(250_000), 12: Money(12_000), 6: Money(0)}
    assert vat.input_vat == Money(100_000)
    assert vat.net == Money(162_000)
    omforing = settlement(chart, journal, dt.date(2026, 6, 30))
    journal = post(journal, omforing)
    # After the omföring: 2611, 2621 and 2641 are zero; 2650 holds kredit 1 620,00.
    balances = {n: a.closing for n, a in ledger(journal).items()}
    assert balances[2611] == balances[2621] == balances[2641] == Money(0)
    assert balances[2650] == -vat.net


def test_eu_purchase_of_goods(chart: Chart, vat_table: VatTable) -> None:
    # Goods for 40 000,00 kr from a company in Germany, no moms on the invoice.
    # Calculated moms 25 % = 40 000 x 0,25 = 10 000,00 kr, booked as both
    # utgående (2614) and ingående (2645); they cancel out, so moms to pay is 0.
    lines = eu_purchase_lines(chart, vat_table, Money(4_000_000), "moms_25",
                              dt.date(2026, 6, 10), goods=True, counter_account=2440)
    journal = post(open_journal(chart), _voucher(*((ln.account, ln.side, ln.amount.ore)
                                                   for ln in lines)))
    vat = report(chart, journal)
    assert vat.eu_goods_purchases == Money(4_000_000)  # ruta 20
    assert vat.reverse_charge_output == Money(1_000_000)  # ruta 30
    assert vat.input_vat == Money(1_000_000)  # ruta 48
    assert vat.net == Money(0)


def test_eu_sale_of_goods(chart: Chart) -> None:
    # Goods for 30 000,00 kr to a VAT registered company in Denmark: no Swedish moms,
    # 30 000,00 kr in ruta 35 and nothing to pay.
    lines = eu_sale_lines(chart, Money(3_000_000), goods=True, counter_account=1510)
    journal = post(open_journal(chart), _voucher(*((ln.account, ln.side, ln.amount.ore)
                                                   for ln in lines)))
    vat = report(chart, journal)
    assert [(ln.account, ln.side) for ln in lines] == [(1510, D), (3108, K)]
    assert vat.eu_goods_sales == Money(3_000_000)  # ruta 35
    assert vat.output_total == Money(0)
    assert vat.net == Money(0)
