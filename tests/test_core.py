"""Tests for the accounting engine in ra.core."""

import datetime as dt
from pathlib import Path

import pytest

from ra.core.chart import Chart, load_chart
from ra.core.depreciation import monthly
from ra.core.formatting import NBSP, format_ore
from ra.core.ledger import Journal, ledger, open_journal, post, trial_balance
from ra.core.money import Money, MoneyTypeError, total
from ra.core.parameters import ParameterTable, load_parameters
from ra.core.payroll import PayrollAccounts, calculate, vouchers
from ra.core.reconciliation import StatementLine, compare
from ra.core.reports import balance_sheet, income_statement
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
def params() -> ParameterTable:
    return load_parameters(CONTENT / "parametrar.yaml")


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


def test_payroll_three_employees(chart: Chart, params: ParameterTable) -> None:
    staff = [(Money(3_200_000), Money(704_000)),    # 32 000,00 brutto, 7 040,00 skatt
             (Money(2_850_000), Money(598_500)),    # 28 500,00 brutto, 5 985,00 skatt
             (Money(4_120_000), Money(1_030_000))]  # 41 200,00 brutto, 10 300,00 skatt
    on = dt.date(2026, 6, 25)
    # Nettolön: 32 000 - 7 040 = 24 960; 28 500 - 5 985 = 22 515; 41 200 - 10 300 = 30 900.
    # Arbetsgivaravgifter 31,42 %: 10 054,40; 8 954,70; 12 945,04.
    slips = [calculate(gross, tax, on, params) for gross, tax in staff]
    assert [s.net for s in slips] == [Money(2_496_000), Money(2_251_500), Money(3_090_000)]
    assert [s.employer_fee for s in slips] == [Money(1_005_440), Money(895_470),
                                               Money(1_294_504)]
    # Totals: brutto 101 700,00; skatt 23 325,00; netto 78 375,00;
    # avgifter 101 700 x 0,3142 = 31 954,14; to skattekontot 23 325 + 31 954,14 = 55 279,14.
    run = vouchers(staff, on, dt.date(2026, 7, 12), params, PayrollAccounts(salary=7210))
    salary = {ln.account: ln.amount for ln in run.salary.lines}
    assert salary == {7210: Money(10_170_000), 2710: Money(2_332_500), 1930: Money(7_837_500)}
    assert run.employer_fee.side_total(D) == Money(3_195_414)
    assert run.tax_payment.side_total(D) == Money(5_527_914)
    journal = open_journal(chart)
    for voucher in (run.salary, run.employer_fee, run.tax_payment):
        journal = post(journal, voucher)
    assert trial_balance(journal).balances


def test_straight_line_plan_36_months() -> None:
    # Inventarier 100 000,00 kr = 10 000 000 öre over 36 months:
    # 10 000 000 / 36 = 277 777,7... -> 277 777 öre per month for 35 months = 9 722 195;
    # last month = 10 000 000 - 9 722 195 = 277 805 öre (takes the 28 öre remainder).
    plan = monthly(Money(10_000_000), 36)
    assert len(plan) == 36
    assert plan[0] == plan[34] == Money(277_777)
    assert plan[35] == Money(277_805)
    assert total(list(plan)) == Money(10_000_000)


def _line(day: int, kronor: str) -> StatementLine:
    return StatementLine(dt.date(2026, 6, day), Money.parse(kronor))


def test_bank_reconciliation() -> None:
    bank = [_line(2, "12 500"), _line(5, "-8 000"), _line(10, "-5 000"), _line(12, "3 750"),
            _line(15, "-1 249"), _line(20, "-2 400"), _line(25, "-78 375"), _line(30, "-125")]
    ledger_lines = [_line(1, "12 500"), _line(5, "-8 000"), _line(8, "-5 000"),
                    _line(12, "3 750"), _line(15, "-1 294"), _line(20, "-2 400"),
                    _line(25, "-78 375")]
    result = compare(bank, ledger_lines, bank_opening=Money.parse("100 000"),
                     ledger_opening=Money.parse("100 000"))
    # Six exact matches (dates up to 2 days apart). The bank fee of 125 kr is missing in the
    # ledger, and the payment of 1 249 kr was booked as 1 294 kr.
    assert len(result.matched) == 6
    assert result.bank_only == (bank[4], bank[7])
    assert result.ledger_only == (ledger_lines[4],)
    # Statement: 100 000 + 12 500 - 8 000 - 5 000 + 3 750 - 1 249 - 2 400 - 78 375 - 125
    #   = 21 101; ledger: 100 000 + 12 500 - 8 000 - 5 000 + 3 750 - 1 294 - 2 400 - 78 375
    #   = 21 181. Difference 21 101 - 21 181 = -80 = -125 (fee) + 45 (1 294 - 1 249).
    assert result.difference == Money.parse("-80")


# The hand calculated month (tests/hand_calculated_month.md). Amounts in kronor.
# Ingående balans 1 juni 2026, debet positive.
HAND_MONTH_OPENING: dict[int, str] = {
    1220: "60 000", 1229: "-12 000", 1460: "40 000", 1510: "25 000", 1930: "180 000",
    2081: "-25 000", 2091: "-138 000", 2350: "-100 000", 2440: "-18 000", 2650: "-12 000",
}
HAND_MONTH: tuple[tuple[int, str, tuple[tuple[int, Side, str], ...]], ...] = (
    (2, "Lokalhyra juni", ((5010, D, "12 000"), (1930, K, "12 000"))),
    (3, "Kundfaktura 1001", ((1510, D, "50 000"), (3001, K, "40 000"), (2611, K, "10 000"))),
    (5, "Leverantörsfaktura varor",
     ((4010, D, "24 000"), (2641, D, "6 000"), (2440, K, "30 000"))),
    (8, "Inbetalning kundfordran", ((1930, D, "25 000"), (1510, K, "25 000"))),
    (10, "Betalning leverantörsskuld", ((2440, D, "18 000"), (1930, K, "18 000"))),
    (12, "Betalning moms maj", ((2650, D, "12 000"), (1930, K, "12 000"))),
    (15, "Inköp varor från Tyskland",
     ((4075, D, "20 000"), (2645, D, "5 000"), (2614, K, "5 000"), (2440, K, "20 000"))),
    (18, "Kortförsäljning", ((1930, D, "6 250"), (3001, K, "5 000"), (2611, K, "1 250"))),
    (20, "Mobiltelefon juni", ((6212, D, "800"), (2641, D, "200"), (1930, K, "1 000"))),
    (25, "Löneutbetalning juni", ((7210, D, "35 000"), (2710, K, "8 400"), (1930, K, "26 600"))),
    (25, "Arbetsgivaravgifter juni", ((7510, D, "10 997"), (2731, K, "10 997"))),
    (28, "Bankavgift", ((6570, D, "150"), (1930, K, "150"))),
    (30, "Avskrivning inventarier", ((7832, D, "1 000"), (1229, K, "1 000"))),
    (30, "Momsomföring juni", ((2611, D, "11 250"), (2614, D, "5 000"), (2641, K, "6 200"),
                               (2645, K, "5 000"), (2650, K, "5 050"))),
)


def _hand_month_journal(chart: Chart) -> Journal:
    journal = open_journal(chart, {n: Money.parse(a) for n, a in HAND_MONTH_OPENING.items()})
    for day, text, lines in HAND_MONTH:
        journal = post(journal, Voucher(
            series="A", date=dt.date(2026, 6, day), text=text,
            lines=tuple(VoucherLine(n, side, Money.parse(a)) for n, side, a in lines)))
    return journal


def test_hand_calculated_month_reports_run(chart: Chart) -> None:
    # Expected råbalans, resultat and balans are filled in by the owner by hand (D2.8);
    # until then this test only checks the engine's own invariants on the month.
    journal = _hand_month_journal(chart)
    result = income_statement(chart, journal)
    balance = balance_sheet(chart, journal)
    assert trial_balance(journal).balances
    assert balance.total_assets == balance.total_equity_and_liabilities
    assert result.net_result == result.result_after_financial_items
