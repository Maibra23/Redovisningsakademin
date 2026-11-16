"""Scenario: Nordvik Kontorsmiljö AB, its ingående balanser and the month's events.

The scenario is content in content/scenario_nordvik. ``load_scenario`` parses the
files and checks them: schemas, references between files, the opening
verifikation against the kontoplan, the open invoices and the inventarie
against the opening balances, and that every organisation number is invented
(it must fail its check digit). ``realise`` turns the calendar into the
reference solution for one seed: each event's parameters are fixed, sampled
from the seed or taken from an earlier event, its recipe gives the document
figures and the accepted verifikation, and the kontoutdrag rows get their
amounts from the movements on 1930. ``check_references`` and ``check_month``
are the checks the content validator adds on top.

Each event names a recipe from ``learning.recipes``, so the simulator and the
exercises share keys. Three month recipes are the scenario's own, because
their key depends on the whole company: the pay run for all employees, its
arbetsgivaravgifter, and the momsomföring of the month's moms.
"""

import datetime as dt
import random
import re
from collections.abc import Callable, Mapping, Set
from dataclasses import dataclass, replace
from pathlib import Path
from types import MappingProxyType
from typing import Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from ra.core import depreciation, payroll, vat
from ra.core.ledger import Journal, PostingError, open_journal, post
from ra.core.money import Money, total
from ra.core.voucher import Side, Voucher, VoucherLine, validate
from ra.learning import recipes
from ra.learning.recipes import RecipeContext, RecipeError, RecipeResult
from ra.learning.schemas import DocumentKind, DocumentTemplate, RangeSpec, TemplateFile

SCENARIO_DIR = "scenario_nordvik"
FILES = {
    "company": "foretag.yaml",
    "parties": "parter.yaml",
    "employees": "anstallda.yaml",
    "opening": "ingaende_balanser.yaml",
    "calendar": "kalender.yaml",
    "statement": "kontoutdrag.yaml",
    "templates": "dokumentmallar.yaml",
}
BANK = recipes.BANK
CUSTOMERS = recipes.CUSTOMERS
SUPPLIERS = recipes.SUPPLIERS
EQUIPMENT = recipes.EQUIPMENT
ACCUMULATED_DEPRECIATION = depreciation.ACCUMULATED_ACCOUNT
PLANTED_DIFFERENCES = 2
MAX_BANK_DELAY_DAYS = 3  # reconciliation.compare matches bank dates at most three days apart

Country = Literal["SE", "DK", "FI"]


class ScenarioError(ValueError):
    """The scenario files are invalid; ``errors`` lists every problem found."""

    def __init__(self, errors: list[str]) -> None:
        super().__init__("\n".join(errors))
        self.errors = errors


class _Model(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class Party(_Model):
    """A customer, supplier or other counterparty, with invented numbers."""

    id: str = Field(min_length=1)
    namn: str = Field(min_length=1)
    land: Country
    ort: str = Field(min_length=1)
    betalningsvillkor_dagar: int = Field(ge=0)
    orgnr: str | None = None
    momsnr: str | None = None


class PartyFile(_Model):
    kunder: tuple[Party, ...] = Field(min_length=1)
    leverantorer: tuple[Party, ...] = Field(min_length=1)
    ovriga: tuple[Party, ...] = ()


class Equipment(_Model):
    """An inventarie in use, depreciated straight line from the month it was bought."""

    id: str = Field(min_length=1)
    beskrivning: str = Field(min_length=1)
    anskaffad: dt.date
    anskaffningsvarde_ore: int = Field(gt=0)
    nyttjandeperiod_ar: int = Field(gt=0)


class Company(_Model):
    """The company profile and its accounting choices (redovisningsval)."""

    namn: str = Field(min_length=1)
    orgnr: str
    momsnr: str
    ort: str = Field(min_length=1)
    verksamhet: str = Field(min_length=1)
    manad: dt.date
    serie: str = Field(min_length=1)
    redovisningsval: tuple[str, ...] = Field(min_length=1)
    inventarier: tuple[Equipment, ...] = ()

    @model_validator(mode="after")
    def _first_of_month(self) -> "Company":
        if self.manad.day != 1:
            raise ValueError("manad must be the first day of the month")
        return self


class Employee(_Model):
    id: str = Field(min_length=1)
    namn: str = Field(min_length=1)
    befattning: str = Field(min_length=1)
    bruttolon_ore: int = Field(gt=0)
    skatt_procent: int = Field(ge=0, le=100)


class EmployeeFile(_Model):
    anstallda: tuple[Employee, ...] = Field(min_length=1)


class OpeningLine(_Model):
    konto: int
    debet_ore: int = Field(default=0, ge=0)
    kredit_ore: int = Field(default=0, ge=0)

    @model_validator(mode="after")
    def _one_side(self) -> "OpeningLine":
        if (self.debet_ore > 0) == (self.kredit_ore > 0):
            raise ValueError("an opening row needs an amount in exactly one of debet and kredit")
        return self


class OpeningVoucher(_Model):
    datum: dt.date
    text: str = Field(min_length=1)
    rader: tuple[OpeningLine, ...] = Field(min_length=2)


class OpenInvoice(_Model):
    """A kundfaktura or leverantörsfaktura still unpaid when the month starts."""

    part: str = Field(min_length=1)
    fakturanummer: str = Field(min_length=1)
    datum: dt.date
    forfallodag: dt.date
    belopp_ore: int = Field(gt=0)


class OpeningFile(_Model):
    verifikation: OpeningVoucher
    kundfakturor: tuple[OpenInvoice, ...] = ()
    leverantorsfakturor: tuple[OpenInvoice, ...] = ()


class Link(_Model):
    """A parameter taken from a figure of an earlier event, such as an invoice's brutto."""

    fran: str = Field(min_length=1)
    figur: str = Field(min_length=1)


EventParam = Link | RangeSpec | int | str | tuple[int | str, ...]


class Event(_Model):
    """One business event in the month and the document it puts in the Inkorg.

    ``kompetens``, ``regel`` and ``tips`` serve grading and feedback as for an
    exercise; ``text`` is the document's text and ``dolda`` the figures it hides.
    """

    id: str = Field(min_length=1)
    datum: dt.date
    titel: str = Field(min_length=1)
    dokument: DocumentKind
    recept: str = Field(min_length=1)
    kompetens: str = Field(min_length=1)
    regel: str = Field(min_length=1)
    tips: str = Field(min_length=1)
    text: str = Field(min_length=1)
    motpart: str | None = None
    fakturanummer: str | None = None
    avser: str | None = None
    parametrar: dict[str, EventParam] = Field(default_factory=dict)
    beskrivning: str | None = None
    dolda: tuple[str, ...] = ()


class Calendar(_Model):
    handelser: tuple[Event, ...] = Field(min_length=1)


class StatementRow(_Model):
    """A kontoutdrag row: an event's bank movement, or a planted difference with its recipe."""

    text: str = Field(min_length=1)
    handelse: str | None = None
    dagar_senare: int = Field(default=0, ge=0, le=MAX_BANK_DELAY_DAYS)
    planterad: bool = False
    datum: dt.date | None = None
    recept: str | None = None
    parametrar: dict[str, EventParam] = Field(default_factory=dict)
    forklaring: str | None = None

    @model_validator(mode="after")
    def _event_or_planted(self) -> "StatementRow":
        if self.handelse is not None:
            if self.planterad or self.datum or self.recept or self.parametrar or self.forklaring:
                raise ValueError("a row with handelse takes only text and dagar_senare")
        elif not (self.planterad and self.datum and self.recept and self.forklaring):
            raise ValueError("a row without handelse must be planterad with datum, recept "
                             "and forklaring")
        return self


class StatementFile(_Model):
    bank: str = Field(min_length=1)
    ingaende_saldo_ore: int
    rader: tuple[StatementRow, ...] = Field(min_length=1)


@dataclass(frozen=True)
class Scenario:
    """The parsed and checked scenario."""

    company: Company
    parties: PartyFile
    employees: tuple[Employee, ...]
    opening: OpeningFile
    events: tuple[Event, ...]
    statement: StatementFile
    templates: Mapping[str, DocumentTemplate]

    @property
    def month_start(self) -> dt.date:
        return self.company.manad

    @property
    def month_end(self) -> dt.date:
        start = self.company.manad
        following = dt.date(start.year + start.month // 12, start.month % 12 + 1, 1)
        return following - dt.timedelta(days=1)

    def party(self, party_id: str) -> Party | None:
        everyone = self.parties.kunder + self.parties.leverantorer + self.parties.ovriga
        return next((p for p in everyone if p.id == party_id), None)

    def event(self, event_id: str) -> Event | None:
        return next((e for e in self.events if e.id == event_id), None)

    def opening_balances(self) -> dict[int, Money]:
        """Ingående balanser, signed with debet positive, as ``ledger.open_journal`` takes them."""
        balances: dict[int, Money] = {}
        for row in self.opening.verifikation.rader:
            amount = Money(row.debet_ore - row.kredit_ore)
            balances[row.konto] = balances.get(row.konto, Money.zero()) + amount
        return balances

    def opening_voucher(self) -> Voucher:
        """The ingående balanser as one verifikation, for display and validation."""
        source = self.opening.verifikation
        lines = tuple(
            VoucherLine(r.konto, Side.DEBET if r.debet_ore else Side.KREDIT,
                        Money(r.debet_ore or r.kredit_ore))
            for r in source.rader)
        return Voucher(self.company.serie, source.datum, source.text, lines)


def _luhn_valid(digits: str) -> bool:
    """Swedish organisationsnummer check digit (Luhn over all ten digits)."""
    checksum = 0
    for index, char in enumerate(digits):
        value = int(char) * (2 if index % 2 == 0 else 1)
        checksum += value - 9 if value > 9 else value
    return checksum % 10 == 0


def _cvr_valid(digits: str) -> bool:
    """Danish CVR check: weights 2, 7, 6, 5, 4, 3, 2, 1 and a sum divisible by 11."""
    return sum(int(c) * w for c, w in zip(digits, (2, 7, 6, 5, 4, 3, 2, 1), strict=True)) % 11 == 0


def _y_tunnus_valid(digits: str) -> bool:
    """Finnish Y-tunnus check digit: weights 7, 9, 10, 5, 8, 4, 2 modulo 11."""
    remainder = sum(int(c) * w for c, w in zip(digits[:7], (7, 9, 10, 5, 8, 4, 2),
                                               strict=True)) % 11
    if remainder == 1:
        return False
    return int(digits[7]) == (0 if remainder == 0 else 11 - remainder)


ORGNR = re.compile(r"\d{6}-\d{4}")
VAT_NUMBERS: Mapping[str, tuple[re.Pattern[str], Callable[[str], bool]]] = MappingProxyType({
    "SE": (re.compile(r"SE(\d{10})01"), _luhn_valid),
    "DK": (re.compile(r"DK(\d{8})"), _cvr_valid),
    "FI": (re.compile(r"FI(\d{8})"), _y_tunnus_valid),
})


def _check_numbers(where: str, country: str, orgnr: str | None, momsnr: str | None) -> list[str]:
    """Numbers must be well formed and fail their check digit, so no real company has them."""
    errors: list[str] = []
    if orgnr is not None:
        if not ORGNR.fullmatch(orgnr):
            errors.append(f"{where}: orgnr {orgnr} is not written NNNNNN-NNNN")
        elif _luhn_valid(orgnr.replace("-", "")):
            errors.append(f"{where}: orgnr {orgnr} has a valid check digit and could be real")
    if momsnr is not None:
        pattern, valid = VAT_NUMBERS[country]
        match = pattern.fullmatch(momsnr)
        if match is None:
            errors.append(f"{where}: momsnr {momsnr} is not a {country} number")
        elif valid(match.group(1)):
            errors.append(f"{where}: momsnr {momsnr} has a valid check digit and could be real")
        elif country == "SE" and orgnr is not None and match.group(1) != orgnr.replace("-", ""):
            errors.append(f"{where}: momsnr {momsnr} does not match orgnr {orgnr}")
    if country != "SE" and momsnr is None:
        errors.append(f"{where}: a party in another EU country needs a momsnr")
    return errors


def _parse(folder: Path, name: str, model: type[BaseModel], errors: list[str]) -> Any:
    path = folder / FILES[name]
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        return model.model_validate(data)
    except (OSError, UnicodeDecodeError, yaml.YAMLError) as error:
        errors.append(f"{path}: cannot be read: {error}")
    except ValidationError as error:
        errors += [f"{path}: {'.'.join(str(p) for p in e['loc'])}: {e['msg']}"
                   for e in error.errors()]
    return None


def load_scenario(folder: Path, ctx: RecipeContext) -> Scenario:
    """Parse the scenario folder and check it; raises ``ScenarioError`` with every problem."""
    errors: list[str] = []
    company = _parse(folder, "company", Company, errors)
    parties = _parse(folder, "parties", PartyFile, errors)
    employees = _parse(folder, "employees", EmployeeFile, errors)
    opening = _parse(folder, "opening", OpeningFile, errors)
    calendar = _parse(folder, "calendar", Calendar, errors)
    statement = _parse(folder, "statement", StatementFile, errors)
    templates = _parse(folder, "templates", TemplateFile, errors)
    if errors:
        raise ScenarioError(errors)
    scenario = Scenario(company, parties, employees.anstallda, opening, calendar.handelser,
                        statement, MappingProxyType({t.id: t for t in templates.mallar}))
    errors = (_check_parties(scenario) + _check_opening(scenario, ctx)
              + _check_calendar(scenario) + _check_statement(scenario))
    if errors:
        raise ScenarioError(errors)
    return scenario


def _duplicates(ids: list[str]) -> list[str]:
    return sorted({i for i in ids if ids.count(i) > 1})


def _check_parties(scenario: Scenario) -> list[str]:
    company = scenario.company
    everyone = scenario.parties.kunder + scenario.parties.leverantorer + scenario.parties.ovriga
    errors = [f"party id {i} is used twice" for i in _duplicates([p.id for p in everyone])]
    errors += [f"employee id {i} is used twice"
               for i in _duplicates([e.id for e in scenario.employees])]
    errors += _check_numbers("foretag", "SE", company.orgnr, company.momsnr)
    for party in everyone:
        errors += _check_numbers(f"party {party.id}", party.land, party.orgnr, party.momsnr)
    return errors


def _months_between(start: dt.date, end: dt.date) -> int:
    return (end.year - start.year) * 12 + end.month - start.month


def _check_opening(scenario: Scenario, ctx: RecipeContext) -> list[str]:
    source = scenario.opening
    voucher = scenario.opening_voucher()
    errors = [f"opening verifikation: {issue.code.value} {issue.account or ''}".rstrip()
              for issue in validate(ctx.chart, voucher)]
    if source.verifikation.datum != scenario.month_start:
        errors.append("opening verifikation must be dated the first day of the month")
    balances = scenario.opening_balances()

    def agrees(account: int, expected: Money, what: str) -> None:
        if balances.get(account, Money.zero()) != expected:
            errors.append(f"opening balance on {account} does not equal {what}")

    customers = {p.id for p in scenario.parties.kunder}
    suppliers = {p.id for p in scenario.parties.leverantorer}
    errors += [f"open kundfaktura {i.fakturanummer}: unknown customer {i.part}"
               for i in source.kundfakturor if i.part not in customers]
    errors += [f"open leverantörsfaktura {i.fakturanummer}: unknown supplier {i.part}"
               for i in source.leverantorsfakturor if i.part not in suppliers]
    numbers = [i.fakturanummer for i in source.kundfakturor + source.leverantorsfakturor]
    errors += [f"open invoice number {n} is used twice" for n in _duplicates(numbers)]
    agrees(CUSTOMERS, total([Money(i.belopp_ore) for i in source.kundfakturor]),
           "the open kundfakturor")
    agrees(SUPPLIERS, -total([Money(i.belopp_ore) for i in source.leverantorsfakturor]),
           "the open leverantörsfakturor")
    equipment = scenario.company.inventarier
    agrees(EQUIPMENT, total([Money(e.anskaffningsvarde_ore) for e in equipment]),
           "the inventariers anskaffningsvärde")
    written_off = [
        total(list(depreciation.monthly(Money(e.anskaffningsvarde_ore),
                                        e.nyttjandeperiod_ar * 12)
                   [:_months_between(e.anskaffad, scenario.month_start)]))
        for e in equipment]
    agrees(ACCUMULATED_DEPRECIATION, -total(written_off), "the depreciation so far")
    if scenario.statement.ingaende_saldo_ore != balances.get(BANK, Money.zero()).ore:
        errors.append(f"kontoutdrag ingående saldo does not equal the opening balance on {BANK}")
    return errors


def _is_month_recipe(name: str) -> bool:
    return name in MONTH_RECIPES


def _check_params(where: str, name: str, params: Mapping[str, Any],
                  earlier: set[str]) -> list[str]:
    if _is_month_recipe(name):
        return [f"{where}: month recipe {name} takes no parametrar"] if params else []
    if name not in recipes.recipe_names():
        return [f"{where}: unknown recipe {name}"]
    errors = [f"{where}: recipe {name} has no parameter {key}"
              for key in params if key not in recipes.get_recipe(name).defaults]
    errors += [f"{where}: {key} refers to {value.fran}, which is not an earlier event"
               for key, value in params.items()
               if isinstance(value, Link) and value.fran not in earlier]
    return errors


def _check_calendar(scenario: Scenario) -> list[str]:
    errors = [f"event id {i} is used twice" for i in _duplicates([e.id for e in scenario.events])]
    open_numbers = {i.fakturanummer for i in
                    scenario.opening.kundfakturor + scenario.opening.leverantorsfakturor}
    earlier: set[str] = set()
    previous = scenario.month_start
    for event in scenario.events:
        where = f"event {event.id}"
        if not scenario.month_start <= event.datum <= scenario.month_end:
            errors.append(f"{where}: datum {event.datum} is outside the month")
        if event.datum < previous:
            errors.append(f"{where}: events must be in date order")
        previous = event.datum
        if event.motpart is not None and scenario.party(event.motpart) is None:
            errors.append(f"{where}: unknown motpart {event.motpart}")
        if event.avser is not None and event.avser not in earlier | open_numbers:
            errors.append(f"{where}: avser {event.avser} is neither an earlier event "
                          "nor an open invoice")
        errors += _check_params(where, event.recept, event.parametrar, earlier)
        earlier.add(event.id)
    return errors


def _check_statement(scenario: Scenario) -> list[str]:
    rows = scenario.statement.rader
    event_ids = {e.id for e in scenario.events}
    linked = [r.handelse for r in rows if r.handelse is not None]
    errors = [f"kontoutdrag: unknown handelse {i}" for i in linked if i not in event_ids]
    errors += [f"kontoutdrag: handelse {i} appears twice" for i in _duplicates(linked)]
    planted = [r for r in rows if r.planterad]
    if len(planted) != PLANTED_DIFFERENCES:
        errors.append(f"kontoutdrag needs exactly {PLANTED_DIFFERENCES} planted rows, "
                      f"found {len(planted)}")
    for row in planted:
        where = f"kontoutdrag row {row.text!r}"
        if row.datum is not None and not scenario.month_start <= row.datum <= scenario.month_end:
            errors.append(f"{where}: datum {row.datum} is outside the month")
        if row.recept is not None:
            if _is_month_recipe(row.recept):
                errors.append(f"{where}: a planted row cannot use a month recipe")
            else:
                errors += _check_params(where, row.recept, row.parametrar, set())
    return errors


MonthRecipe = Callable[[RecipeContext, Scenario, Journal, dt.date], RecipeResult]


def _pay_run(ctx: RecipeContext, scenario: Scenario, on_date: dt.date) -> tuple[
        payroll.PayrollVouchers, dict[str, Money | int | str]]:
    """All employees' pay run with ``recipes.tax_withheld``; per person and total figures."""
    people = [(Money(e.bruttolon_ore), recipes.tax_withheld(Money(e.bruttolon_ore),
                                                            e.skatt_procent))
              for e in scenario.employees]
    runs = payroll.vouchers(people, on_date, on_date, ctx.params,
                            payroll.PayrollAccounts(salary=recipes.SALARIES_SALARIED),
                            scenario.company.serie)
    figures: dict[str, Money | int | str] = {}
    for employee, (gross, tax) in zip(scenario.employees, people, strict=True):
        slip = payroll.calculate(gross, tax, on_date, ctx.params)
        figures |= {f"bruttolon_{employee.id}": slip.gross,
                    f"skatteavdrag_{employee.id}": slip.tax_withheld,
                    f"nettolon_{employee.id}": slip.net}
    fee = runs.employer_fee.side_total(Side.DEBET)
    gross_total = total([g for g, _ in people])
    tax_total = total([t for _, t in people])
    figures |= {"bruttolon": gross_total, "skatteavdrag": tax_total,
                "nettolon": gross_total - tax_total, "arbetsgivaravgifter": fee,
                "avgiftssats": recipes.percent_text(
                    ctx.params.value_for(payroll.EMPLOYER_FEE_KEY, on_date))}
    return runs, figures


def _salaries(ctx: RecipeContext, scenario: Scenario, journal: Journal,
              on_date: dt.date) -> RecipeResult:
    """Löneverifikation for the month: debet 7210, kredit 2710 and 1930."""
    runs, figures = _pay_run(ctx, scenario, on_date)
    return RecipeResult(MappingProxyType(figures), runs.salary)


def _employer_fees(ctx: RecipeContext, scenario: Scenario, journal: Journal,
                   on_date: dt.date) -> RecipeResult:
    """Arbetsgivaravgifter on the month's summed bruttolön: debet 7510, kredit 2731."""
    runs, figures = _pay_run(ctx, scenario, on_date)
    return RecipeResult(MappingProxyType(figures), runs.employer_fee)


def _vat_settlement(ctx: RecipeContext, scenario: Scenario, journal: Journal,
                    on_date: dt.date) -> RecipeResult:
    """Momsomföring of the month's moms to 2650, computed by core from the journal."""
    period = {"period_from": scenario.month_start, "period_to": on_date}
    voucher = vat.settlement(ctx.chart, journal, on_date, scenario.company.serie, **period)
    month = vat.report(ctx.chart, journal, **period)
    figures = {"utgaende_moms": month.output_total, "ingaende_moms": month.input_vat,
               "moms_att_betala": month.net}
    return RecipeResult(MappingProxyType(figures), voucher)


MONTH_RECIPES: Mapping[str, MonthRecipe] = MappingProxyType({
    "lon_manad": _salaries,
    "arbetsgivaravgifter_manad": _employer_fees,
    "momsomforing_manad": _vat_settlement,
})


@dataclass(frozen=True)
class RealisedEvent:
    """One event with its parameters for this seed and its recipe result (the key)."""

    event: Event
    parameters: Mapping[str, int | str]
    result: RecipeResult


@dataclass(frozen=True)
class BankRow:
    """One kontoutdrag row; ``amount`` is signed, a deposit positive."""

    on_date: dt.date
    text: str
    amount: Money
    event_id: str | None = None
    planted: RecipeResult | None = None
    explanation: str | None = None


@dataclass(frozen=True)
class Month:
    """The reference solution for one seed: every event's key posted after the opening."""

    seed: int
    events: tuple[RealisedEvent, ...]
    journal: Journal
    statement_opening: Money
    statement: tuple[BankRow, ...]

    @property
    def statement_closing(self) -> Money:
        return self.statement_opening + total([r.amount for r in self.statement])

    @property
    def planted(self) -> tuple[BankRow, ...]:
        return tuple(r for r in self.statement if r.planted is not None)


def _resolve(where: str, name: str, given: Mapping[str, Any], rng: random.Random,
             figures: Mapping[str, Mapping[str, Any]]) -> dict[str, int | str]:
    """Fixed values as written, ranges and lists sampled, links read from earlier figures."""
    specs = {**recipes.get_recipe(name).defaults, **given}
    values: dict[str, int | str] = {}
    for key in sorted(specs):
        spec = specs[key]
        if isinstance(spec, Link):
            figure = figures.get(spec.fran, {}).get(spec.figur)
            if not isinstance(figure, Money):
                raise ScenarioError([f"{where}: {spec.fran} has no amount {spec.figur}"])
            values[key] = figure.ore
        elif isinstance(spec, RangeSpec | tuple):
            values[key] = recipes.sample_value(spec, rng)
        else:
            values[key] = spec
    return values


def _bank_movement(voucher: Voucher) -> Money:
    return total([ln.amount if ln.side is Side.DEBET else -ln.amount
                  for ln in voucher.lines if ln.account == BANK])


def _in_series(voucher: Voucher, series: str) -> Voucher:
    return replace(voucher, series=series)


def realise(scenario: Scenario, ctx: RecipeContext, seed: int) -> Month:
    """The reference solution for ``seed``; raises ``ScenarioError`` if an event cannot run."""
    journal = open_journal(ctx.chart, scenario.opening_balances())
    realised: list[RealisedEvent] = []
    figures: dict[str, Mapping[str, Any]] = {}
    for event in scenario.events:
        where = f"event {event.id} (seed {seed})"
        rng = random.Random(f"{seed}:{event.id}")
        try:
            if _is_month_recipe(event.recept):
                parameters: dict[str, int | str] = {}
                result = MONTH_RECIPES[event.recept](ctx, scenario, journal, event.datum)
            else:
                parameters = _resolve(where, event.recept, event.parametrar, rng, figures)
                result = recipes.run(ctx, event.recept, event.datum, parameters)
            result = replace(result, voucher=_in_series(result.voucher, scenario.company.serie))
            journal = post(journal, result.voucher)
        except ScenarioError:
            raise
        except (RecipeError, PostingError, ValueError) as error:
            raise ScenarioError([f"{where}: {error}"]) from error
        realised.append(RealisedEvent(event, MappingProxyType(parameters), result))
        figures[event.id] = result.figures
    by_id = {r.event.id: r for r in realised}
    rows = [_statement_row(scenario, ctx, seed, index, row, by_id)
            for index, row in enumerate(scenario.statement.rader)]
    rows.sort(key=lambda r: r.on_date)
    return Month(seed, tuple(realised), journal,
                 Money(scenario.statement.ingaende_saldo_ore), tuple(rows))


def _statement_row(scenario: Scenario, ctx: RecipeContext, seed: int, index: int,
                   row: StatementRow, by_id: Mapping[str, RealisedEvent]) -> BankRow:
    where = f"kontoutdrag row {row.text!r} (seed {seed})"
    if row.handelse is not None:
        source = by_id[row.handelse]
        amount = _bank_movement(source.result.voucher)
        if amount.ore == 0:
            raise ScenarioError([f"{where}: event {row.handelse} does not move {BANK}"])
        on_date = source.event.datum + dt.timedelta(days=row.dagar_senare)
        return BankRow(on_date, row.text, amount, event_id=row.handelse)
    recipe, on_date = row.recept or "", row.datum or scenario.month_end
    rng = random.Random(f"{seed}:kontoutdrag:{index}")
    try:
        parameters = _resolve(where, recipe, row.parametrar, rng, {})
        result = recipes.run(ctx, recipe, on_date, parameters)
    except RecipeError as error:
        raise ScenarioError([f"{where}: {error}"]) from error
    result = replace(result, voucher=_in_series(result.voucher, scenario.company.serie))
    amount = _bank_movement(result.voucher)
    if amount.ore == 0:
        raise ScenarioError([f"{where}: recipe {recipe} does not move {BANK}"])
    return BankRow(on_date, row.text, amount, planted=result, explanation=row.forklaring)


def check_references(scenario: Scenario, skills: Set[str], rules: Set[str]) -> list[str]:
    """Every event's kompetens and regel exist in the content library."""
    errors = [f"event {e.id}: unknown kompetens {e.kompetens}"
              for e in scenario.events if e.kompetens not in skills]
    return errors + [f"event {e.id}: unknown regel {e.regel}"
                     for e in scenario.events if e.regel not in rules]


def check_month(month: Month) -> list[str]:
    """Every event that moves the bank account is on the kontoutdrag."""
    on_statement = {r.event_id for r in month.statement if r.event_id}
    return [f"event {r.event.id} moves {BANK} but is not on the kontoutdrag (seed {month.seed})"
            for r in month.events
            if _bank_movement(r.result.voucher).ore and r.event.id not in on_statement]
