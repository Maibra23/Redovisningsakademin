"""One test per recipe with hand calculated figures (arithmetic in each comment).

Amounts are öre: 1 000 000 öre is 10 000,00 kr. Dates are in June 2026.
"""

import datetime as dt
from pathlib import Path

import pytest

from ra.core.voucher import Side
from ra.learning import recipes

CONTENT = Path(__file__).resolve().parents[1] / "content"
ON = dt.date(2026, 6, 15)
D, K = Side.DEBET, Side.KREDIT

# (recipe, parameters, expected key lines as (account, side, öre))
CASES: list[tuple[str, dict[str, int | str], set[tuple[int, Side, int]]]] = [
    # 10 000 kr x 25 % = 2 500 kr moms; 10 000 + 2 500 = 12 500 kr to 1510.
    ("forsaljning_faktura", {"netto_ore": 1_000_000, "momskod": "moms_25"},
     {(1510, D, 1_250_000), (3001, K, 1_000_000), (2611, K, 250_000)}),
    # 2 000 kr x 25 % = 500 kr; the sale reversed: 2 000 + 500 = 2 500 kr off 1510.
    ("kreditfaktura", {"netto_ore": 200_000, "momskod": "moms_25"},
     {(3001, D, 200_000), (2611, D, 50_000), (1510, K, 250_000)}),
    # 12 500 kr received from the customer.
    ("inbetalning_kund", {"belopp_ore": 1_250_000}, {(1930, D, 1_250_000), (1510, K, 1_250_000)}),
    # 4 000 kr x 25 % = 1 000 kr moms; 4 000 + 1 000 = 5 000 kr to 2440.
    ("leverantorsfaktura_kostnad", {"netto_ore": 400_000, "kostnad": "kontorsmateriel"},
     {(6110, D, 400_000), (2641, D, 100_000), (2440, K, 500_000)}),
    # 12 345 kr x 25 % = 3 086,25 kr; 12 345 + 3 086,25 = 15 431,25 kr.
    ("leverantorsfaktura_varor", {"netto_ore": 1_234_500},
     {(4010, D, 1_234_500), (2641, D, 308_625), (2440, K, 1_543_125)}),
    # 15 431,25 kr paid to the supplier.
    ("utbetalning_leverantor", {"belopp_ore": 1_543_125},
     {(2440, D, 1_543_125), (1930, K, 1_543_125)}),
    # Gross 499 kr; moms = 499 x 25 / 125 = 99,80 kr; netto 499 - 99,80 = 399,20 kr.
    ("kortkop_kvitto", {"brutto_ore": 49_900},
     {(6110, D, 39_920), (2641, D, 9_980), (1930, K, 49_900)}),
    # Gross 312,50 kr; moms = 312,50 x 25 / 125 = 62,50 kr; netto 250 kr; owed to the employee.
    ("utlagg", {"brutto_ore": 31_250},
     {(6110, D, 25_000), (2641, D, 6_250), (2890, K, 31_250)}),
    # 125 kr bank fee, no moms.
    ("bankavgift", {"belopp_ore": 12_500}, {(6570, D, 12_500), (1930, K, 12_500)}),
    # 15 000 kr rent without moms paid from the bank.
    ("hyra", {"belopp_ore": 1_500_000}, {(5010, D, 1_500_000), (1930, K, 1_500_000)}),
    # 40 000 kr x 25 % = 10 000 kr; 40 000 + 10 000 = 50 000 kr.
    ("inkop_inventarie", {"netto_ore": 4_000_000},
     {(1220, D, 4_000_000), (2641, D, 1_000_000), (2440, K, 5_000_000)}),
    # 6 000 kr x 25 % = 1 500 kr; 6 000 + 1 500 = 7 500 kr.
    ("inkop_forbrukningsinventarie", {"netto_ore": 600_000},
     {(5410, D, 600_000), (2641, D, 150_000), (2440, K, 750_000)}),
    # 36 000 kr over 3 years = 36 months; 36 000 / 36 = 1 000 kr per month.
    ("manadsavskrivning", {"anskaffning_ore": 3_600_000, "ar": 3},
     {(7832, D, 100_000), (1229, K, 100_000)}),
    # 34 567 kr x 30 % = 10 370,10 kr, rounded down to whole kronor 10 370 kr;
    # nettolön 34 567 - 10 370 = 24 197 kr.
    ("loneverifikation", {"bruttolon_ore": 3_456_700, "skatt_procent": 30},
     {(7210, D, 3_456_700), (2710, K, 1_037_000), (1930, K, 2_419_700)}),
    # 34 567 kr x 31,42 % = 10 860,9514 kr, rounded to 10 860,95 kr.
    ("arbetsgivaravgifter", {"bruttolon_ore": 3_456_700, "skatt_procent": 30},
     {(7510, D, 1_086_095), (2731, K, 1_086_095)}),
    # Skatteavdrag 10 370 kr + arbetsgivaravgifter 10 860,95 kr = 21 230,95 kr.
    ("betalning_skattekonto", {"bruttolon_ore": 3_456_700, "skatt_procent": 30},
     {(1630, D, 2_123_095), (1930, K, 2_123_095)}),
    # Next month's rent 15 000 kr moved from 5010 to the balansräkning.
    ("forutbetald_kostnad", {"belopp_ore": 1_500_000},
     {(1710, D, 1_500_000), (5010, K, 1_500_000)}),
    # 4 500 kr of this month's redovisningstjänster, invoice not yet received.
    ("upplupen_kostnad", {"belopp_ore": 450_000}, {(6530, D, 450_000), (2990, K, 450_000)}),
    # Utgående 80 000 kr x 25 % = 20 000 kr; ingående 20 000 kr x 25 % = 5 000 kr;
    # to pay 20 000 - 5 000 = 15 000 kr.
    ("momsomforing", {"forsaljning_netto_ore": 8_000_000, "inkop_netto_ore": 2_000_000},
     {(2611, D, 2_000_000), (2641, K, 500_000), (2650, K, 1_500_000)}),
    # 15 000 kr moms paid from the bank.
    ("momsbetalning", {"belopp_ore": 1_500_000}, {(2650, D, 1_500_000), (1930, K, 1_500_000)}),
    # 20 000 kr x 25 % = 5 000 kr calculated moms, booked both as ingående and utgående.
    ("eu_inkop_varor", {"netto_ore": 2_000_000},
     {(4075, D, 2_000_000), (2645, D, 500_000), (2614, K, 500_000), (2440, K, 2_000_000)}),
    # 8 000 kr x 25 % = 2 000 kr calculated moms.
    ("eu_inkop_tjanst", {"netto_ore": 800_000},
     {(4535, D, 800_000), (2645, D, 200_000), (2614, K, 200_000), (2440, K, 800_000)}),
    # 30 000 kr without moms.
    ("eu_forsaljning_varor", {"netto_ore": 3_000_000},
     {(1510, D, 3_000_000), (3108, K, 3_000_000)}),
    # 12 000 kr without moms.
    ("eu_forsaljning_tjanst", {"netto_ore": 1_200_000},
     {(1510, D, 1_200_000), (3308, K, 1_200_000)}),
]


@pytest.fixture(scope="module")
def ctx() -> recipes.RecipeContext:
    return recipes.load_context(CONTENT)


@pytest.mark.parametrize(("name", "parameters", "expected"), CASES, ids=[c[0] for c in CASES])
def test_recipe_key(ctx: recipes.RecipeContext, name: str, parameters: dict[str, int | str],
                    expected: set[tuple[int, Side, int]]) -> None:
    voucher = recipes.run(ctx, name, ON, parameters).voucher
    assert {(line.account, line.side, line.amount.ore) for line in voucher.lines} == expected


def test_sale_at_12_and_6_procent(ctx: recipes.RecipeContext) -> None:
    # 10 000 kr x 12 % = 1 200 kr, total 11 200 kr; 10 000 kr x 6 % = 600 kr, total 10 600 kr.
    at_12 = recipes.run(ctx, "forsaljning_faktura", ON, {"netto_ore": 1_000_000,
                                                         "momskod": "moms_12"}).voucher
    at_6 = recipes.run(ctx, "forsaljning_faktura", ON, {"netto_ore": 1_000_000,
                                                        "momskod": "moms_6"}).voucher
    assert {(ln.account, ln.side, ln.amount.ore) for ln in at_12.lines} == {
        (1510, D, 1_120_000), (3002, K, 1_000_000), (2621, K, 120_000)}
    assert {(ln.account, ln.side, ln.amount.ore) for ln in at_6.lines} == {
        (1510, D, 1_060_000), (3003, K, 1_000_000), (2631, K, 60_000)}
