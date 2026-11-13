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
from pathlib import Path
from types import MappingProxyType
from typing import Any

from ra.core.chart import Chart, load_chart
from ra.core.money import Money
from ra.core.parameters import ParameterTable, load_parameters
from ra.core.vat import VatTable, load_vat_table
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
