"""Recipes: sampled parameters in, document figures and the answer key out.

A recipe takes parameters (amounts in öre, choices as text) and calls
``core`` to produce the figures shown on the document and the accepted
verifikation. The key therefore always agrees with the engine. Where practice
accepts more than one account for a row, ``alternatives`` maps the key's
account to the other accepted accounts.

Parameters are sampled from a seed, so the same exercise id and seed always
give the same numbers. Account numbers are BAS accounts from
content/kontoplan.yaml; the content validator runs every recipe and checks
each key against the kontoplan.
"""

import datetime as dt
import random
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from decimal import Decimal
from fractions import Fraction
from pathlib import Path
from types import MappingProxyType
from typing import Any

from ra.core import depreciation, payroll
from ra.core.chart import Chart, load_chart
from ra.core.ledger import open_journal, post
from ra.core.money import Money
from ra.core.parameters import ParameterTable, load_parameters
from ra.core.vat import (
    VatAmounts,
    VatTable,
    eu_purchase_lines,
    eu_sale_lines,
    load_vat_table,
    settlement,
)
from ra.core.voucher import Side, Voucher, VoucherLine
from ra.learning.schemas import ParamSpec, RangeSpec

D, K = Side.DEBET, Side.KREDIT
SERIES = "A"
# Exercise dates fall in this year; rates are looked up by the sampled date.
EXERCISE_YEAR = 2026
LAST_SAFE_DAY = 28
VAT_25 = "moms_25"

BANK = 1930  # Företagskonto
CUSTOMERS = 1510  # Kundfordringar
SUPPLIERS = 2440  # Leverantörsskulder
INPUT_VAT = 2641  # Debiterad ingående moms
GOODS_PURCHASES = 4010  # Inköp av handelsvaror i Sverige
EQUIPMENT = 1220  # Inventarier, verktyg och installationer
TAX_ACCOUNT = 1630  # Avräkning för skatter och avgifter (skattekonto)
PREPAID_RENT = 1710  # Förutbetalda hyreskostnader
OTHER_PREPAID = 1790  # Övriga förutbetalda kostnader och upplupna intäkter
VAT_SETTLEMENT = 2650  # Redovisningskonto för moms
OTHER_SHORT_TERM_LIABILITIES = 2890  # Övriga kortfristiga skulder
EMPLOYEE_LIABILITIES = 2820  # Kortfristiga skulder till anställda
OTHER_ACCRUED = 2990  # Övriga upplupna kostnader och förutbetalda intäkter
PREMISES_RENT = 5010  # Lokalhyra
SMALL_EQUIPMENT = 5410  # Förbrukningsinventarier
OFFICE_SUPPLIES = 6110  # Kontorsmateriel
ACCOUNTING_SERVICES = 6530  # Redovisningstjänster
BANK_COSTS = 6570  # Bankkostnader
SALARIES_SALARIED = 7210  # Löner till tjänstemän


class RecipeError(ValueError):
    """Unknown recipe or parameter, or a parameter value the recipe cannot use."""


@dataclass(frozen=True)
class RecipeContext:
    """Kontoplan, momssatser and dated parameters the recipes compute with."""

    chart: Chart
    vat: VatTable
    params: ParameterTable


@dataclass(frozen=True)
class RecipeResult:
    """Document figures, the accepted verifikation and accepted alternative accounts."""

    figures: Mapping[str, Money | int | str]
    voucher: Voucher
    alternatives: Mapping[int, frozenset[int]] = field(
        default_factory=lambda: MappingProxyType({})
    )


Builder = Callable[[RecipeContext, dt.date, Mapping[str, Any]], RecipeResult]


@dataclass(frozen=True)
class Recipe:
    name: str
    defaults: Mapping[str, ParamSpec]
    build: Builder


@dataclass(frozen=True)
class Generated:
    """One generated exercise instance: date, parameters and the recipe result."""

    on_date: dt.date
    parameters: Mapping[str, int | str]
    result: RecipeResult


_REGISTRY: dict[str, Recipe] = {}


def recipe(name: str, **defaults: ParamSpec) -> Callable[[Builder], Builder]:
    """Register a recipe under ``name`` with its default parameter ranges."""

    def register(build: Builder) -> Builder:
        if name in _REGISTRY:
            raise RecipeError(f"Recipe {name} is registered twice")
        _REGISTRY[name] = Recipe(name, MappingProxyType(dict(defaults)), build)
        return build

    return register


def get_recipe(name: str) -> Recipe:
    try:
        return _REGISTRY[name]
    except KeyError:
        raise RecipeError(f"Unknown recipe {name}") from None


def recipe_names() -> tuple[str, ...]:
    return tuple(sorted(_REGISTRY))


def load_context(content_root: Path) -> RecipeContext:
    """Read the kontoplan, momssatser and parametrar from the content folder."""
    return RecipeContext(
        chart=load_chart(content_root / "kontoplan.yaml"),
        vat=load_vat_table(content_root / "momssatser.yaml"),
        params=load_parameters(content_root / "parametrar.yaml"),
    )


def _sample_value(spec: ParamSpec, rng: random.Random) -> int | str:
    if isinstance(spec, RangeSpec):
        return spec.min + spec.steg * rng.randint(0, (spec.max - spec.min) // spec.steg)
    return rng.choice(spec)


def sample(
    name: str, seed: int, overrides: Mapping[str, ParamSpec] | None = None
) -> tuple[dt.date, dict[str, int | str]]:
    """Seeded date and parameters for a recipe; ``overrides`` narrow the default ranges."""
    entry = get_recipe(name)
    unknown = set(overrides or {}) - set(entry.defaults)
    if unknown:
        raise RecipeError(f"Recipe {name} has no parameters {sorted(unknown)}")
    specs = {**entry.defaults, **(overrides or {})}
    rng = random.Random(seed)
    on_date = dt.date(EXERCISE_YEAR, rng.randint(1, 12), rng.randint(1, LAST_SAFE_DAY))
    return on_date, {key: _sample_value(specs[key], rng) for key in sorted(specs)}


def run(ctx: RecipeContext, name: str, on_date: dt.date,
        parameters: Mapping[str, int | str]) -> RecipeResult:
    """Run a recipe with fixed parameters (used for worked examples and by ``generate``)."""
    entry = get_recipe(name)
    missing = set(entry.defaults) - set(parameters)
    if missing:
        raise RecipeError(f"Recipe {name} is missing parameters {sorted(missing)}")
    return entry.build(ctx, on_date, parameters)


def generate(ctx: RecipeContext, name: str, seed: int,
             overrides: Mapping[str, ParamSpec] | None = None) -> Generated:
    """Sample parameters from ``seed`` and run the recipe."""
    on_date, parameters = sample(name, seed, overrides)
    return Generated(on_date, MappingProxyType(parameters),
                     run(ctx, name, on_date, parameters))


def _amount(parameters: Mapping[str, Any], key: str) -> Money:
    value = parameters[key]
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise RecipeError(f"{key} must be a positive whole number of öre, got {value!r}")
    return Money(value)


def _choice(parameters: Mapping[str, Any], key: str, options: Mapping[str, Any]) -> Any:
    value = parameters[key]
    if value not in options:
        raise RecipeError(f"{key} must be one of {sorted(options)}, got {value!r}")
    return options[value]


def _voucher(on_date: dt.date, text: str, *lines: tuple[int, Side, Money]) -> Voucher:
    return Voucher(SERIES, on_date, text, tuple(VoucherLine(a, s, m) for a, s, m in lines))


def _alternatives(pairs: Mapping[int, set[int]]) -> Mapping[int, frozenset[int]]:
    return MappingProxyType({k: frozenset(v) for k, v in pairs.items()})


@dataclass(frozen=True)
class CostType:
    """A cost account a recipe can choose, with what the document calls it."""

    account: int
    description: str
    alternatives: frozenset[int] = frozenset()


# Purchases of services and goods for the company's own use. Kontorsmateriel
# is also commonly booked on 5460 Förbrukningsmaterial, so both are accepted.
COST_TYPES: Mapping[str, CostType] = MappingProxyType({
    "kontorsmateriel": CostType(6110, "Kontorsmateriel", frozenset({5460})),
    "it_tjanster": CostType(6540, "IT-tjänster, support och drift"),
    "redovisning": CostType(6530, "Redovisningstjänster"),
    "annonsering": CostType(5910, "Annonsering"),
})
SUPPLIER_INVOICE_AMOUNT = RangeSpec(min=50_000, max=2_500_000, steg=10_000)


def _purchase_on_invoice(ctx: RecipeContext, on_date: dt.date, net: Money, account: int,
                         description: str) -> tuple[dict[str, Money | int | str], Voucher]:
    amounts = ctx.vat.add(net, VAT_25, on_date)
    figures: dict[str, Money | int | str] = {
        "netto": amounts.net, "moms": amounts.vat, "brutto": amounts.gross,
        "momssats": int(ctx.vat.rate_for(VAT_25, on_date)), "beskrivning": description,
    }
    voucher = _voucher(on_date, "Leverantörsfaktura",
                       (account, D, amounts.net), (INPUT_VAT, D, amounts.vat),
                       (SUPPLIERS, K, amounts.gross))
    return figures, voucher


@recipe("leverantorsfaktura_kostnad", netto_ore=SUPPLIER_INVOICE_AMOUNT,
        kostnad=tuple(COST_TYPES))
def supplier_invoice_cost(ctx: RecipeContext, on_date: dt.date,
                          p: Mapping[str, Any]) -> RecipeResult:
    """Inköp mot faktura: debet kostnad (netto) and ingående moms, kredit leverantörsskulder."""
    cost: CostType = _choice(p, "kostnad", COST_TYPES)
    figures, voucher = _purchase_on_invoice(ctx, on_date, _amount(p, "netto_ore"),
                                            cost.account, cost.description)
    return RecipeResult(MappingProxyType(figures), voucher,
                        _alternatives({cost.account: set(cost.alternatives)}
                                      if cost.alternatives else {}))


@recipe("leverantorsfaktura_varor", netto_ore=SUPPLIER_INVOICE_AMOUNT)
def supplier_invoice_goods(ctx: RecipeContext, on_date: dt.date,
                           p: Mapping[str, Any]) -> RecipeResult:
    """Inköp av handelsvaror mot faktura: debet 4010 (netto) and ingående moms, kredit 2440."""
    figures, voucher = _purchase_on_invoice(ctx, on_date, _amount(p, "netto_ore"),
                                            GOODS_PURCHASES, "Handelsvaror för vidareförsäljning")
    return RecipeResult(MappingProxyType(figures), voucher)


@recipe("utbetalning_leverantor", belopp_ore=SUPPLIER_INVOICE_AMOUNT)
def supplier_payment(ctx: RecipeContext, on_date: dt.date,
                     p: Mapping[str, Any]) -> RecipeResult:
    """Utbetalning till leverantör: debet leverantörsskulder, kredit företagskonto."""
    amount = _amount(p, "belopp_ore")
    voucher = _voucher(on_date, "Betalning av leverantörsfaktura",
                       (SUPPLIERS, D, amount), (BANK, K, amount))
    return RecipeResult(MappingProxyType({"belopp": amount}), voucher)


# Descriptions by moms code. "livsmedel" has a dated rate (12 procent, 6 procent from
# 1 April 2026 to 31 December 2027), so its accounts follow the rate on the sale date.
SALE_DESCRIPTIONS: Mapping[str, str] = MappingProxyType({
    "moms_25": "Skrivbord och kontorsstolar",
    "moms_12": "Catering till kundens konferens",
    "moms_6": "Facklitteratur om arbetsmiljö",
    "livsmedel": "Livsmedel till kundens personalrestaurang",
})
SALE_AMOUNT = RangeSpec(min=200_000, max=5_000_000, steg=10_000)
SALE_VAT_CODES = tuple(SALE_DESCRIPTIONS)


@dataclass(frozen=True)
class Sale:
    """A sale in Sverige: amounts, document figures and the two accounts it credits."""

    amounts: VatAmounts
    figures: Mapping[str, Money | int | str]
    revenue: int
    output_vat: int


def _sale(ctx: RecipeContext, on_date: dt.date, p: Mapping[str, Any]) -> Sale:
    """Amounts and accounts for a sale in Sverige at the rate of ``momskod``."""
    code = _choice(p, "momskod", {c: c for c in SALE_VAT_CODES})
    rate = ctx.vat.rate_for(code, on_date)
    revenue = ctx.chart.by_moms_role(f"forsaljning_{rate}")
    output_vat = ctx.chart.by_moms_role(f"utgaende_{rate}")
    if rate.denominator != 1 or not revenue or not output_vat:
        raise RecipeError(f"No sales accounts for a rate of {rate} procent")
    amounts = ctx.vat.add(_amount(p, "netto_ore"), code, on_date)
    figures: dict[str, Money | int | str] = {
        "netto": amounts.net, "moms": amounts.vat, "brutto": amounts.gross,
        "momssats": int(rate), "beskrivning": SALE_DESCRIPTIONS[code],
    }
    return Sale(amounts, MappingProxyType(figures), revenue[0].number, output_vat[0].number)


def _sale_voucher(on_date: dt.date, sale: Sale) -> Voucher:
    return _voucher(on_date, "Kundfaktura", (CUSTOMERS, D, sale.amounts.gross),
                    (sale.revenue, K, sale.amounts.net), (sale.output_vat, K, sale.amounts.vat))


@recipe("forsaljning_faktura", netto_ore=SALE_AMOUNT, momskod=SALE_VAT_CODES)
def sale_on_invoice(ctx: RecipeContext, on_date: dt.date, p: Mapping[str, Any]) -> RecipeResult:
    """Försäljning mot faktura: debet 1510, kredit försäljning (netto) and utgående moms."""
    sale = _sale(ctx, on_date, p)
    return RecipeResult(sale.figures, _sale_voucher(on_date, sale))


@recipe("kreditfaktura", netto_ore=RangeSpec(min=50_000, max=1_000_000, steg=5_000),
        momskod=SALE_VAT_CODES)
def credit_note(ctx: RecipeContext, on_date: dt.date, p: Mapping[str, Any]) -> RecipeResult:
    """Kreditfaktura to a customer: the sale reversed, debet försäljning and moms, kredit 1510."""
    sale = _sale(ctx, on_date, p)
    voucher = _voucher(on_date, "Kreditfaktura", (sale.revenue, D, sale.amounts.net),
                       (sale.output_vat, D, sale.amounts.vat), (CUSTOMERS, K, sale.amounts.gross))
    return RecipeResult(sale.figures, voucher)


@recipe("inbetalning_kund", belopp_ore=SALE_AMOUNT)
def customer_payment(ctx: RecipeContext, on_date: dt.date, p: Mapping[str, Any]) -> RecipeResult:
    """Inbetalning från kund: debet företagskonto, kredit kundfordringar."""
    amount = _amount(p, "belopp_ore")
    voucher = _voucher(on_date, "Inbetalning från kund", (BANK, D, amount), (CUSTOMERS, K, amount))
    return RecipeResult(MappingProxyType({"belopp": amount}), voucher)


def _receipt(ctx: RecipeContext, on_date: dt.date, gross: Money, text: str,
             credit_account: int, credit_alternatives: frozenset[int] = frozenset()
             ) -> RecipeResult:
    """Kontorsmateriel paid in full with moms 25 procent inside the gross amount."""
    cost = COST_TYPES["kontorsmateriel"]
    amounts = ctx.vat.split(gross, VAT_25, on_date)
    figures: dict[str, Money | int | str] = {
        "netto": amounts.net, "moms": amounts.vat, "brutto": amounts.gross,
        "momssats": int(ctx.vat.rate_for(VAT_25, on_date)), "beskrivning": cost.description,
    }
    voucher = _voucher(on_date, text, (cost.account, D, amounts.net),
                       (INPUT_VAT, D, amounts.vat), (credit_account, K, amounts.gross))
    alternatives = {cost.account: set(cost.alternatives)}
    if credit_alternatives:
        alternatives[credit_account] = set(credit_alternatives)
    return RecipeResult(MappingProxyType(figures), voucher, _alternatives(alternatives))


RECEIPT_AMOUNT = RangeSpec(min=5_000, max=300_000, steg=100)


@recipe("kortkop_kvitto", brutto_ore=RECEIPT_AMOUNT)
def card_purchase(ctx: RecipeContext, on_date: dt.date, p: Mapping[str, Any]) -> RecipeResult:
    """Kortköp med kvitto, betalkort mot företagskontot: kredit 1930 with the gross amount."""
    return _receipt(ctx, on_date, _amount(p, "brutto_ore"), "Kortköp", BANK)


@recipe("utlagg", brutto_ore=RECEIPT_AMOUNT)
def employee_outlay(ctx: RecipeContext, on_date: dt.date, p: Mapping[str, Any]) -> RecipeResult:
    """Utlägg: an employee paid privately; the company owes the gross amount.

    Kredit 2890 Övriga kortfristiga skulder, as the common vendor guides do; 2820
    Kortfristiga skulder till anställda is accepted as well.
    """
    return _receipt(ctx, on_date, _amount(p, "brutto_ore"), "Utlägg anställd",
                    OTHER_SHORT_TERM_LIABILITIES, frozenset({EMPLOYEE_LIABILITIES}))


@recipe("bankavgift", belopp_ore=RangeSpec(min=2_500, max=25_000, steg=500))
def bank_fee(ctx: RecipeContext, on_date: dt.date, p: Mapping[str, Any]) -> RecipeResult:
    """Bankavgift, without moms: debet bankkostnader, kredit företagskonto."""
    amount = _amount(p, "belopp_ore")
    voucher = _voucher(on_date, "Bankavgift", (BANK_COSTS, D, amount), (BANK, K, amount))
    return RecipeResult(MappingProxyType({"belopp": amount}), voucher)


RENT_AMOUNT = RangeSpec(min=800_000, max=4_000_000, steg=50_000)


@recipe("hyra", belopp_ore=RENT_AMOUNT)
def rent(ctx: RecipeContext, on_date: dt.date, p: Mapping[str, Any]) -> RecipeResult:
    """Lokalhyra for the month without moms, paid from the bank: debet 5010, kredit 1930."""
    amount = _amount(p, "belopp_ore")
    voucher = _voucher(on_date, "Lokalhyra", (PREMISES_RENT, D, amount), (BANK, K, amount))
    return RecipeResult(MappingProxyType({"belopp": amount}), voucher)


@recipe("inkop_inventarie", netto_ore=RangeSpec(min=3_000_000, max=15_000_000, steg=50_000))
def equipment_purchase(ctx: RecipeContext, on_date: dt.date,
                       p: Mapping[str, Any]) -> RecipeResult:
    """Inköp av inventarie mot faktura: debet 1220 (netto) and ingående moms, kredit 2440."""
    figures, voucher = _purchase_on_invoice(ctx, on_date, _amount(p, "netto_ore"), EQUIPMENT,
                                            "Kontorsmöbler till företagets egna lokaler")
    return RecipeResult(MappingProxyType(figures), voucher)


@recipe("inkop_forbrukningsinventarie",
        netto_ore=RangeSpec(min=100_000, max=1_200_000, steg=10_000))
def small_equipment_purchase(ctx: RecipeContext, on_date: dt.date,
                             p: Mapping[str, Any]) -> RecipeResult:
    """Förbrukningsinventarier mot faktura: debet 5410 (netto) and ingående moms, kredit 2440."""
    figures, voucher = _purchase_on_invoice(ctx, on_date, _amount(p, "netto_ore"),
                                            SMALL_EQUIPMENT, "Skrivbordslampor och hyllor")
    return RecipeResult(MappingProxyType(figures), voucher)


@recipe("manadsavskrivning", anskaffning_ore=RangeSpec(min=3_000_000, max=15_000_000,
                                                       steg=60_000), ar=(3, 5))
def monthly_depreciation(ctx: RecipeContext, on_date: dt.date,
                         p: Mapping[str, Any]) -> RecipeResult:
    """Månadsavskrivning, linjär plan: debet 7832, kredit 1229 with the first month's amount."""
    years = _choice(p, "ar", {3: 3, 5: 5})
    cost = _amount(p, "anskaffning_ore")
    amount = depreciation.monthly(cost, years * 12)[0]
    figures = {"anskaffningsvarde": cost, "avskrivning": amount, "nyttjandeperiod": years}
    return RecipeResult(MappingProxyType(figures), depreciation.voucher(amount, on_date, SERIES))


SALARY_AMOUNT = RangeSpec(min=2_500_000, max=5_500_000, steg=10_000)
TAX_PERCENTS = (28, 30, 32)


def _pay_run(ctx: RecipeContext, on_date: dt.date,
             p: Mapping[str, Any]) -> tuple[payroll.PayrollVouchers, dict[str, Money | str]]:
    """One tjänsteman's pay run. The skatteavdrag is given as a share of the bruttolön,
    rounded down to whole kronor as a skattetabell gives it; tax tables are not modelled."""
    gross = _amount(p, "bruttolon_ore")
    percent = _choice(p, "skatt_procent", {v: v for v in TAX_PERCENTS})
    tax = Money(gross.percent(percent).ore // 100 * 100)
    slip = payroll.calculate(gross, tax, on_date, ctx.params)
    runs = payroll.vouchers([(gross, tax)], on_date, on_date, ctx.params,
                            payroll.PayrollAccounts(salary=SALARIES_SALARIED), SERIES)
    rate = ctx.params.value_for(payroll.EMPLOYER_FEE_KEY, on_date)
    figures: dict[str, Money | str] = {
        "bruttolon": slip.gross, "skatteavdrag": slip.tax_withheld, "nettolon": slip.net,
        "arbetsgivaravgifter": slip.employer_fee,
        "summa": slip.tax_withheld + slip.employer_fee, "avgiftssats": _percent_text(rate),
    }
    return runs, figures


def _percent_text(rate: Fraction) -> str:
    """A rate in Swedish notation, 31,42 rather than 31.42."""
    return str(Decimal(rate.numerator) / Decimal(rate.denominator)).replace(".", ",")


@recipe("loneverifikation", bruttolon_ore=SALARY_AMOUNT, skatt_procent=TAX_PERCENTS)
def salary(ctx: RecipeContext, on_date: dt.date, p: Mapping[str, Any]) -> RecipeResult:
    """Löneverifikation: debet 7210 bruttolön, kredit 2710 skatteavdrag and 1930 nettolön."""
    runs, figures = _pay_run(ctx, on_date, p)
    return RecipeResult(MappingProxyType(figures), runs.salary)


@recipe("arbetsgivaravgifter", bruttolon_ore=SALARY_AMOUNT, skatt_procent=TAX_PERCENTS)
def employer_fees(ctx: RecipeContext, on_date: dt.date, p: Mapping[str, Any]) -> RecipeResult:
    """Arbetsgivaravgifter on the bruttolön: debet 7510, kredit 2731."""
    runs, figures = _pay_run(ctx, on_date, p)
    return RecipeResult(MappingProxyType(figures), runs.employer_fee)


@recipe("betalning_skattekonto", bruttolon_ore=SALARY_AMOUNT, skatt_procent=TAX_PERCENTS)
def tax_account_payment(ctx: RecipeContext, on_date: dt.date,
                        p: Mapping[str, Any]) -> RecipeResult:
    """Skatteavdrag plus arbetsgivaravgifter paid to the skattekonto: debet 1630, kredit 1930."""
    runs, figures = _pay_run(ctx, on_date, p)
    return RecipeResult(MappingProxyType(figures), runs.tax_payment)


@recipe("forutbetald_kostnad", belopp_ore=RENT_AMOUNT)
def prepaid_expense(ctx: RecipeContext, on_date: dt.date, p: Mapping[str, Any]) -> RecipeResult:
    """Förutbetald kostnad at month end: next month's rent, already expensed on 5010, is moved
    to the balansräkning: debet 1710, kredit 5010. 1790 is also accepted."""
    amount = _amount(p, "belopp_ore")
    voucher = _voucher(on_date, "Förutbetald hyra", (PREPAID_RENT, D, amount),
                       (PREMISES_RENT, K, amount))
    return RecipeResult(MappingProxyType({"belopp": amount}), voucher,
                        _alternatives({PREPAID_RENT: {OTHER_PREPAID}}))


@recipe("upplupen_kostnad", belopp_ore=RangeSpec(min=200_000, max=1_500_000, steg=10_000))
def accrued_expense(ctx: RecipeContext, on_date: dt.date, p: Mapping[str, Any]) -> RecipeResult:
    """Upplupen kostnad at month end, invoice not yet received: debet 6530, kredit 2990.
    Moms is booked when the invoice arrives, so the accrual is without moms."""
    amount = _amount(p, "belopp_ore")
    figures = {"belopp": amount, "beskrivning": "Redovisningstjänster för månaden"}
    voucher = _voucher(on_date, "Upplupen kostnad", (ACCOUNTING_SERVICES, D, amount),
                       (OTHER_ACCRUED, K, amount))
    return RecipeResult(MappingProxyType(figures), voucher)


@recipe("momsomforing", forsaljning_netto_ore=RangeSpec(min=5_000_000, max=20_000_000,
                                                        steg=10_000),
        inkop_netto_ore=RangeSpec(min=1_000_000, max=4_000_000, steg=10_000))
def vat_settlement(ctx: RecipeContext, on_date: dt.date, p: Mapping[str, Any]) -> RecipeResult:
    """Momsomföring after one sale and one purchase at 25 procent, computed by vat.settlement."""
    sale = _sale(ctx, on_date, {"momskod": VAT_25, "netto_ore": p["forsaljning_netto_ore"]})
    purchase_net = _amount(p, "inkop_netto_ore")
    _, purchase_voucher = _purchase_on_invoice(ctx, on_date, purchase_net, OFFICE_SUPPLIES,
                                               "Kontorsmateriel")
    journal = post(post(open_journal(ctx.chart), _sale_voucher(on_date, sale)), purchase_voucher)
    voucher = settlement(ctx.chart, journal, on_date, SERIES)
    deductible = ctx.vat.add(purchase_net, VAT_25, on_date).vat
    result_figures = {"utgaende_moms": sale.amounts.vat, "ingaende_moms": deductible,
                      "moms_att_betala": sale.amounts.vat - deductible}
    return RecipeResult(MappingProxyType(result_figures), voucher)


@recipe("momsbetalning", belopp_ore=RangeSpec(min=500_000, max=5_000_000, steg=100))
def vat_payment(ctx: RecipeContext, on_date: dt.date, p: Mapping[str, Any]) -> RecipeResult:
    """Momsbetalning: Skatteverket charges the skattekonto with the period's moms.

    Debet 2650, kredit 1630. The transfer from the bank to the skattekonto is its
    own verifikation (debet 1630, kredit 1930), as in the betalning_skattekonto recipe.
    """
    amount = _amount(p, "belopp_ore")
    voucher = _voucher(on_date, "Moms dragen från skattekontot", (VAT_SETTLEMENT, D, amount),
                       (TAX_ACCOUNT, K, amount))
    return RecipeResult(MappingProxyType({"belopp": amount}), voucher)


EU_AMOUNT = RangeSpec(min=500_000, max=8_000_000, steg=10_000)


def _eu_purchase(ctx: RecipeContext, on_date: dt.date, p: Mapping[str, Any], goods: bool,
                 description: str) -> RecipeResult:
    net = _amount(p, "netto_ore")
    lines = eu_purchase_lines(ctx.chart, ctx.vat, net, VAT_25, on_date, goods=goods,
                              counter_account=SUPPLIERS)
    vat = ctx.vat.add(net, VAT_25, on_date).vat
    figures = {"netto": net, "moms": vat, "momssats": int(ctx.vat.rate_for(VAT_25, on_date)),
               "beskrivning": description}
    voucher = Voucher(SERIES, on_date, "Inköp från annat EU-land", lines)
    return RecipeResult(MappingProxyType(figures), voucher)


@recipe("eu_inkop_varor", netto_ore=EU_AMOUNT)
def eu_goods_purchase(ctx: RecipeContext, on_date: dt.date, p: Mapping[str, Any]) -> RecipeResult:
    """Köp av varor från annat EU-land: debet 4075 and 2645, kredit 2614 and 2440."""
    return _eu_purchase(ctx, on_date, p, True, "Kontorsstolar för vidareförsäljning")


@recipe("eu_inkop_tjanst", netto_ore=EU_AMOUNT)
def eu_service_purchase(ctx: RecipeContext, on_date: dt.date,
                        p: Mapping[str, Any]) -> RecipeResult:
    """Köp av tjänst från annat EU-land: debet 4535 and 2645, kredit 2614 and 2440."""
    return _eu_purchase(ctx, on_date, p, False, "Konsulttjänst, utveckling av webbutik")


def _eu_sale(ctx: RecipeContext, on_date: dt.date, p: Mapping[str, Any], goods: bool,
             description: str) -> RecipeResult:
    net = _amount(p, "netto_ore")
    lines = eu_sale_lines(ctx.chart, net, goods=goods, counter_account=CUSTOMERS)
    voucher = Voucher(SERIES, on_date, "Försäljning till annat EU-land", lines)
    return RecipeResult(MappingProxyType({"netto": net, "beskrivning": description}), voucher)


@recipe("eu_forsaljning_varor", netto_ore=EU_AMOUNT)
def eu_goods_sale(ctx: RecipeContext, on_date: dt.date, p: Mapping[str, Any]) -> RecipeResult:
    """Försäljning av varor till företag i annat EU-land, no moms: debet 1510, kredit 3108."""
    return _eu_sale(ctx, on_date, p, True, "Skrivbord och kontorsstolar")


@recipe("eu_forsaljning_tjanst", netto_ore=EU_AMOUNT)
def eu_service_sale(ctx: RecipeContext, on_date: dt.date, p: Mapping[str, Any]) -> RecipeResult:
    """Försäljning av tjänst till företag i annat EU-land, no moms: debet 1510, kredit 3308."""
    return _eu_sale(ctx, on_date, p, False, "Ergonomikonsultation på kundens kontor")
