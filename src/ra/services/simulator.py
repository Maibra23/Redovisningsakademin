"""Simulator use cases: start, inbox, document, submit, correct, reports, reset.

The learner keeps the books of Nordvik Kontorsmiljö AB for one month. A run is
identified by a seed kept in the learner's settings; the documents and their
keys are realised from the scenario with that seed, so amounts differ per run.
``submit`` validates the verifikation with core, evaluates it against the
event's recipe solution and, in one transaction, stores the verifikation, the
attempt and the skill state. Stored verifikationer are never changed or
deleted: ``correct`` adds a new verifikation that points at the old one, and
``reset`` starts a new run with a new seed. Reports are recomputed from the
stored lines on every call.
"""

import datetime as dt
import secrets
import uuid
from collections.abc import Sequence
from dataclasses import dataclass, replace
from functools import lru_cache

from sqlalchemy.orm import Session

from ra.core import reports as core_reports
from ra.core import vat
from ra.core.ledger import Journal, ledger, open_journal, post, trial_balance
from ra.core.money import Money
from ra.core.voucher import IssueCode, Side, Voucher, VoucherKey, VoucherLine, validate
from ra.learning import feedback
from ra.learning.grading import Grade
from ra.learning.recipes import RecipeResult
from ra.paths import content_root
from ra.services import practice
from ra.services.formatting import format_date, format_ore
from ra.services.views import (
    BalanceSheetView,
    CompanyView,
    DocumentView,
    InboxItemView,
    InboxView,
    IncomeStatementView,
    InputProblem,
    LedgerAccountView,
    LedgerEntryView,
    ReportLineView,
    RowInput,
    SimReportsView,
    SimSubmitResult,
    SimVoucherView,
    TrialBalanceRowView,
    TrialBalanceView,
    VatReportView,
    document_view,
    feedback_view,
    voucher_view,
)
from ra.simulator import documents, evaluate
from ra.simulator.scenario import SCENARIO_DIR, Event, Month, Scenario, load_scenario, realise
from ra.storage import queries
from ra.storage.db import new_session

SEED_SETTING = "sim_seed"
CONTEXT = "simulator"
MAX_VOUCHERS = 500  # per learner and run, architecture section 5
OPENING_LABEL = "IB"
STATUS_NEW, STATUS_BOOKED, STATUS_CORRECTED = "ny", "bokford", "rattad"
ISSUE_PROBLEMS = {
    IssueCode.UNBALANCED: InputProblem.OBALANS,
    IssueCode.TOO_FEW_LINES: InputProblem.OBALANS,
    IssueCode.MISSING_TEXT: InputProblem.TEXT_SAKNAS,
    IssueCode.UNKNOWN_ACCOUNT: InputProblem.KONTO_SAKNAS,
    IssueCode.NON_POSITIVE_AMOUNT: InputProblem.BELOPP_OLASLIGT,
}


class SimulatorError(LookupError):
    """Unknown document or verifikation for this learner's run."""


@lru_cache(maxsize=1)
def scenario() -> Scenario:
    """The scenario, loaded and checked once per process."""
    return load_scenario(content_root() / SCENARIO_DIR, practice.recipe_context())


@lru_cache(maxsize=16)
def _month(seed: int) -> Month:
    return realise(scenario(), practice.recipe_context(), seed)


@dataclass(frozen=True)
class Stored:
    """A stored verifikation as core sees it, with its database id and links."""

    row_id: int
    voucher: Voucher
    document_id: str | None
    corrects_id: int | None


def _stored(session: Session, learner_id: uuid.UUID, seed: int) -> list[Stored]:
    rows = queries.sim_vouchers(session, learner_id, seed)
    by_id = {v.id: v for v, _ in rows}
    stored = []
    for row, lines in rows:
        target = by_id.get(row.corrects_id) if row.corrects_id is not None else None
        voucher = Voucher(
            row.series, row.entry_date, row.text,
            tuple(VoucherLine(ln.account_no, Side.DEBET if ln.debit_ore else Side.KREDIT,
                              Money(ln.debit_ore or ln.credit_ore)) for ln in lines),
            row.number, VoucherKey(target.series, target.number) if target else None)
        stored.append(Stored(row.id, voucher, row.document_id, row.corrects_id))
    return stored


def _journal(stored: Sequence[Stored], without: str | None = None) -> Journal:
    """The learner's journal. ``without`` leaves out one document's verifikationer, for a
    key that depends on the other bookings; links are dropped then, as numbers shift."""
    journal = open_journal(practice.recipe_context().chart, scenario().opening_balances())
    for item in stored:
        if without is not None and item.document_id == without:
            continue
        voucher = replace(item.voucher, number=None)
        journal = post(journal, voucher if without is None else replace(voucher, corrects=None))
    return journal


def _label(voucher: Voucher) -> str:
    return f"{voucher.series} {voucher.number}"


def _groups(stored: Sequence[Stored]) -> dict[str, list[Stored]]:
    groups: dict[str, list[Stored]] = {}
    for item in stored:
        if item.document_id is not None:
            groups.setdefault(item.document_id, []).append(item)
    return groups


def _new_seed(session: Session, learner_id: uuid.UUID) -> int:
    used = queries.sim_seeds(session, learner_id)
    seed = secrets.randbelow(practice.SEED_LIMIT)
    while seed in used:
        seed = secrets.randbelow(practice.SEED_LIMIT)
    queries.save_setting(session, learner_id, SEED_SETTING, seed)
    return seed


def _seed(session: Session, learner_id: uuid.UUID) -> int:
    """The seed of the learner's current run; the first call starts a run."""
    seed = queries.learner_settings(session, learner_id).get(SEED_SETTING)
    return seed if isinstance(seed, int) else _new_seed(session, learner_id)


def company() -> CompanyView:
    sc = scenario()
    profile = sc.company
    return CompanyView(profile.namn, profile.orgnr, profile.momsnr, profile.verksamhet,
                       format_date(sc.month_start).split(" ", 1)[1],
                       format_date(sc.month_start), format_date(sc.month_end),
                       profile.redovisningsval)


def start(learner_id: uuid.UUID) -> CompanyView:
    """Make sure the learner has a run, and describe the company."""
    with new_session() as session, session.begin():
        _seed(session, learner_id)
    return company()


def reset(learner_id: uuid.UUID) -> None:
    """Start over with a new seed and new amounts. The old run's verifikationer stay
    stored and unchanged; they belong to the old seed and are no longer shown."""
    with new_session() as session, session.begin():
        _new_seed(session, learner_id)


def _grade(sc: Scenario, month: Month, event: Event, group: Sequence[Stored],
           stored: Sequence[Stored]) -> tuple[Grade, RecipeResult]:
    solution = evaluate.key(practice.recipe_context(), sc, month, event,
                            _journal(stored, without=event.id))
    grade = evaluate.grade_group(practice.recipe_context().chart, solution,
                                 [g.voucher.lines for g in group])
    return grade, solution


def _item(sc: Scenario, month: Month, event: Event, groups: dict[str, list[Stored]],
          stored: Sequence[Stored]) -> InboxItemView:
    group = groups.get(event.id, [])
    if not group:
        status, correct = STATUS_NEW, None
    else:
        corrected = any(g.corrects_id is not None for g in group)
        status = STATUS_CORRECTED if corrected else STATUS_BOOKED
        correct = _grade(sc, month, event, group, stored)[0].correct
    party = sc.party(event.motpart) if event.motpart else None
    return InboxItemView(event.id, format_date(event.datum), event.titel, event.dokument,
                         party.namn if party else sc.company.namn, status, correct,
                         tuple(_label(g.voucher) for g in group))


def inbox(learner_id: uuid.UUID) -> InboxView:
    """The documents that have arrived, in date order, with their status."""
    with new_session() as session, session.begin():
        seed = _seed(session, learner_id)
        stored = _stored(session, learner_id, seed)
    sc, month = scenario(), _month(seed)
    groups = _groups(stored)
    shown = documents.visible(sc, set(groups))
    return InboxView(
        current_day=format_date(documents.current_day(sc, set(groups))),
        items=tuple(_item(sc, month, e, groups, stored) for e in shown),
        waiting=len(sc.events) - len(shown),
        done=all(e.id in groups for e in sc.events))


def document(learner_id: uuid.UUID, event_id: str) -> DocumentView:
    """One document from the Inkorg, laid out for the document viewer."""
    with new_session() as session, session.begin():
        seed = _seed(session, learner_id)
        stored = _stored(session, learner_id, seed)
    sc, month = scenario(), _month(seed)
    if event_id not in {e.id for e in documents.visible(sc, set(_groups(stored)))}:
        raise SimulatorError(f"Document {event_id} is not in the Inkorg")
    realised = next(r for r in month.events if r.event.id == event_id)
    return document_view(documents.render(sc, practice.library("sv").templates, realised))


def _refusal(sc: Scenario, voucher: Voucher, count: int) -> tuple[InputProblem, ...]:
    """Why a verifikation cannot be stored, as real systems refuse it."""
    problems = [ISSUE_PROBLEMS[i.code] for i in validate(practice.recipe_context().chart,
                                                         voucher)]
    if not sc.month_start <= voucher.date <= sc.month_end:
        problems.append(InputProblem.DATUM_UTANFOR)
    if count >= MAX_VOUCHERS:
        problems.append(InputProblem.FOR_MANGA)
    return tuple(dict.fromkeys(problems))


def _next_number(stored: Sequence[Stored], series: str) -> int:
    return max((s.voucher.number or 0 for s in stored if s.voucher.series == series),
               default=0) + 1


def _store(session: Session, learner_id: uuid.UUID, seed: int, voucher: Voucher,
           event_id: str, corrects_id: int | None) -> None:
    queries.add_sim_voucher(session, {
        "learner_id": learner_id, "sim_seed": seed, "series": voucher.series,
        "number": voucher.number, "entry_date": voucher.date, "text": voucher.text,
        "document_id": event_id, "corrects_id": corrects_id,
    }, [{"account_no": ln.account,
         "debit_ore": ln.amount.ore if ln.side is Side.DEBET else 0,
         "credit_ore": ln.amount.ore if ln.side is Side.KREDIT else 0} for ln in voucher.lines])


def _result(lang: str, event: Event, grade: Grade, solution: RecipeResult, label: str,
            recorded: practice.Recorded) -> SimSubmitResult:
    chart, texts = practice.recipe_context().chart, practice.feedback_texts(lang)
    built = feedback.build(grade, evaluate.as_exercise(event),
                           practice.library(lang).rules[event.regel], texts,
                           feedback.kontering_treatment(texts, chart, solution))
    return SimSubmitResult(feedback=feedback_view(chart, built), voucher_label=label,
                           xp=recorded.xp, total_xp=recorded.total_xp,
                           attempt_no=recorded.attempt_no)


def submit(learner_id: uuid.UUID, event_id: str, rows: Sequence[RowInput],
           entry_date: dt.date, text: str, lang: str) -> SimSubmitResult:
    """Bokför a document: refuse what core rejects, else store, grade and give feedback."""
    lines, problems = practice.parse_rows(rows)
    if problems:
        return SimSubmitResult(problems=problems)
    sc, chart = scenario(), practice.recipe_context().chart
    voucher = Voucher(sc.company.serie, entry_date, text.strip(), lines)
    with new_session() as session, session.begin():
        seed = _seed(session, learner_id)
        stored = _stored(session, learner_id, seed)
        groups = _groups(stored)
        event = sc.event(event_id)
        if event is None or event not in documents.visible(sc, set(groups)):
            return SimSubmitResult(problems=(InputProblem.INTE_I_INKORGEN,))
        if event.id in groups:
            return SimSubmitResult(problems=(InputProblem.REDAN_BOKFORD,))
        refusal = _refusal(sc, voucher, len(stored))
        if refusal:
            return SimSubmitResult(problems=refusal, totals=voucher_view(chart, lines))
        numbered = replace(voucher, number=_next_number(stored, voucher.series))
        grade, solution = _grade(sc, _month(seed), event, [Stored(0, numbered, event.id, None)],
                                 stored)
        _store(session, learner_id, seed, numbered, event.id, None)
        recorded = practice.record_graded(session, learner_id, evaluate.as_exercise(event),
                                          seed, grade, 0, CONTEXT, practice.today())
    return _result(lang, event, grade, solution, _label(numbered), recorded)


def correct(learner_id: uuid.UUID, voucher_id: int, rows: Sequence[RowInput],
            entry_date: dt.date, text: str, lang: str) -> SimSubmitResult:
    """Rättelse: a new verifikation that points at the stored one; the old stays unchanged.

    The document is graded again on the net effect of all its verifikationer.
    """
    lines, problems = practice.parse_rows(rows)
    if problems:
        return SimSubmitResult(problems=problems)
    sc, chart = scenario(), practice.recipe_context().chart
    with new_session() as session, session.begin():
        seed = _seed(session, learner_id)
        stored = _stored(session, learner_id, seed)
        target = next((s for s in stored if s.row_id == voucher_id), None)
        event = sc.event(target.document_id) if target and target.document_id else None
        if target is None or event is None:
            raise SimulatorError(f"Verifikation {voucher_id} is not in this run")
        key = VoucherKey(target.voucher.series, target.voucher.number or 0)
        voucher = Voucher(sc.company.serie, entry_date, text.strip(), lines, corrects=key)
        refusal = _refusal(sc, voucher, len(stored))
        if refusal:
            return SimSubmitResult(problems=refusal, totals=voucher_view(chart, lines))
        numbered = replace(voucher, number=_next_number(stored, voucher.series))
        group = [*_groups(stored)[event.id], Stored(0, numbered, event.id, target.row_id)]
        grade, solution = _grade(sc, _month(seed), event, group, stored)
        _store(session, learner_id, seed, numbered, event.id, target.row_id)
        recorded = practice.record_graded(session, learner_id, evaluate.as_exercise(event),
                                          seed, grade, 0, CONTEXT, practice.today())
    return _result(lang, event, grade, solution, _label(numbered), recorded)


def _amount(money: Money) -> str:
    return format_ore(money.ore) if money.ore else ""


def _voucher_views(stored: Sequence[Stored]) -> tuple[SimVoucherView, ...]:
    chart, sc = practice.recipe_context().chart, scenario()
    opening = sc.opening_voucher()
    views = [SimVoucherView(None, OPENING_LABEL, format_date(opening.date), opening.text, None,
                            None, (), voucher_view(chart, opening.lines))]
    labels = {s.row_id: _label(s.voucher) for s in stored}
    for item in stored:
        corrected_by = tuple(labels[s.row_id] for s in stored if s.corrects_id == item.row_id)
        views.append(SimVoucherView(
            item.row_id, labels[item.row_id], format_date(item.voucher.date), item.voucher.text,
            item.document_id, labels.get(item.corrects_id) if item.corrects_id else None,
            corrected_by, voucher_view(chart, item.voucher.lines)))
    return tuple(views)


def _ledger_views(journal: Journal) -> tuple[LedgerAccountView, ...]:
    chart = journal.chart
    views = []
    for number, account in ledger(journal).items():
        entries = tuple(
            LedgerEntryView(format_date(v.date), _label(v), v.text,
                            _amount(ln.amount) if ln.side is Side.DEBET else "",
                            _amount(ln.amount) if ln.side is Side.KREDIT else "")
            for v in journal.vouchers for ln in v.lines if ln.account == number)
        views.append(LedgerAccountView(
            number, chart[number].name, format_ore(account.opening.ore),
            format_ore(account.debet.ore), format_ore(account.kredit.ore),
            format_ore(account.closing.ore), entries))
    return tuple(views)


def _trial_balance_view(journal: Journal) -> TrialBalanceView:
    balance = trial_balance(journal)
    rows = tuple(
        TrialBalanceRowView(a.number, journal.chart[a.number].name,
                            format_ore(a.closing.ore) if a.closing.ore > 0 else "",
                            format_ore(-a.closing.ore) if a.closing.ore < 0 else "")
        for a in balance.accounts if a.closing.ore)
    return TrialBalanceView(rows, format_ore(balance.total_debet.ore),
                            format_ore(balance.total_kredit.ore), balance.balances)


def _lines(lines: Sequence[core_reports.ReportLine]) -> tuple[ReportLineView, ...]:
    return tuple(ReportLineView(ln.label, format_ore(ln.amount.ore)) for ln in lines)


def _vat_view(journal: Journal) -> VatReportView:
    sc = scenario()
    month = vat.report(journal.chart, journal, sc.month_start, sc.month_end)
    rows = (
        ("10", month.output_by_rate.get(25, Money.zero())),
        ("11", month.output_by_rate.get(12, Money.zero())),
        ("12", month.output_by_rate.get(6, Money.zero())),
        ("20", month.eu_goods_purchases), ("21", month.eu_services_purchases),
        ("30", month.reverse_charge_output), ("35", month.eu_goods_sales),
        ("39", month.eu_services_sales), ("48", month.input_vat),
    )
    return VatReportView(tuple((code, format_ore(amount.ore)) for code, amount in rows),
                         format_ore(abs(month.net.ore)), month.net.ore >= 0)


def reports(learner_id: uuid.UUID) -> SimReportsView:
    """Verifikationslista, huvudbok, råbalans, resultaträkning, balansräkning and momsrapport,
    all computed by core from the learner's stored verifikationer."""
    with new_session() as session, session.begin():
        seed = _seed(session, learner_id)
        stored = _stored(session, learner_id, seed)
    journal = _journal(stored)
    chart = journal.chart
    income = core_reports.income_statement(chart, journal)
    balance = core_reports.balance_sheet(chart, journal)
    return SimReportsView(
        vouchers=_voucher_views(stored),
        ledger=_ledger_views(journal),
        trial_balance=_trial_balance_view(journal),
        income=IncomeStatementView(
            _lines(income.operating), format_ore(income.operating_result.ore),
            _lines(income.financial), format_ore(income.result_after_financial_items.ore),
            _lines(income.tax), format_ore(income.net_result.ore)),
        balance=BalanceSheetView(
            _lines(balance.assets), format_ore(balance.total_assets.ore),
            _lines(balance.equity_and_liabilities),
            format_ore(balance.total_equity_and_liabilities.ore),
            balance.total_assets == balance.total_equity_and_liabilities),
        vat=_vat_view(journal))
