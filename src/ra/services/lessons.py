"""Lesson use cases: the module list with progress and one lesson with its worked example.

A lesson is done when every Kontroll item has been answered correctly at
least once. The worked example (Visa) is computed by its recipe with fixed
parameters; its effect on the resultaträkning and the balansräkning comes
from core.reports on a journal holding that one verifikation.
"""

import uuid
from dataclasses import dataclass

from ra.core.chart import Chart
from ra.core.ledger import open_journal, post
from ra.core.money import Money
from ra.core.reports import ReportLine, balance_sheet, income_statement
from ra.core.voucher import Voucher
from ra.learning import documents, recipes
from ra.learning.schemas import Lesson, Rule
from ra.services import practice
from ra.services.formatting import format_ore
from ra.services.views import DocumentView, VoucherView, document_view, voucher_view
from ra.storage import queries
from ra.storage.db import new_session

KONTROLL = "kontroll"


class LessonError(LookupError):
    """Unknown lesson."""


@dataclass(frozen=True)
class LessonSummary:
    lesson_id: str
    title: str
    done: bool


@dataclass(frozen=True)
class ModuleView:
    module_id: str
    title: str
    description: str
    lessons: tuple[LessonSummary, ...]

    @property
    def done_count(self) -> int:
        return sum(lesson.done for lesson in self.lessons)


@dataclass(frozen=True)
class RuleRef:
    rule_id: str
    reference: str
    title: str


@dataclass(frozen=True)
class EffectLine:
    """One report line the example changes, with the change as signed text."""

    label: str
    amount: str


@dataclass(frozen=True)
class ExampleView:
    text: str
    document: DocumentView
    voucher: VoucherView
    income_lines: tuple[EffectLine, ...]
    balance_assets: tuple[EffectLine, ...]
    balance_equity_liabilities: tuple[EffectLine, ...]
    total_assets: str
    total_equity_liabilities: str


@dataclass(frozen=True)
class LessonView:
    lesson_id: str
    module_id: str
    module_title: str
    title: str
    vad: str
    varfor: str
    hur: str
    nar: str
    simplification: str | None
    rules: tuple[RuleRef, ...]
    example: ExampleView
    exercise_ids: tuple[str, ...]
    check_ids: tuple[str, ...]
    done: bool


def rule_reference(rule: Rule) -> str:
    """"Bokföringslag (1999:1078) 5 kap. 7 §", or the source and lagrum for guidance."""
    return f"{rule.namn} {rule.lagrum}"


def _done_lessons(learner_id: uuid.UUID, lessons: list[Lesson]) -> set[str]:
    checks = [e.id for lesson in lessons for e in lesson.kontroll]
    with new_session() as session:
        correct = queries.correct_items(session, learner_id, checks)
    return {lesson.id for lesson in lessons if all(e.id in correct for e in lesson.kontroll)}


def modules(learner_id: uuid.UUID, lang: str) -> tuple[ModuleView, ...]:
    """Every module with lessons, in order, with each lesson's done flag."""
    lib = practice.library(lang)
    lessons = sorted(lib.lessons.values(), key=lambda lesson: lesson.id)
    done = _done_lessons(learner_id, lessons)
    views = []
    for module in sorted(lib.modules.values(), key=lambda m: m.id):
        own = tuple(LessonSummary(lesson.id, lesson.titel, lesson.id in done)
                    for lesson in lessons if lesson.modul == module.id)
        if own:
            views.append(ModuleView(module.id, module.titel, module.beskrivning, own))
    return tuple(views)


def _effect_lines(lines: tuple[ReportLine, ...]) -> tuple[EffectLine, ...]:
    return tuple(EffectLine(line.label, _signed(line.amount)) for line in lines if line.amount)


def _signed(amount: Money) -> str:
    text = format_ore(amount.ore)
    return text if amount.ore < 0 else f"+{text}"


def _example(chart: Chart, voucher: Voucher, text: str, document: DocumentView) -> ExampleView:
    journal = post(open_journal(chart), voucher)
    income = income_statement(chart, journal)
    balance = balance_sheet(chart, journal)
    return ExampleView(
        text=text,
        document=document,
        voucher=voucher_view(chart, voucher.lines),
        income_lines=_effect_lines(income.operating + income.financial + income.tax),
        balance_assets=_effect_lines(balance.assets),
        balance_equity_liabilities=_effect_lines(balance.equity_and_liabilities),
        total_assets=_signed(balance.total_assets),
        total_equity_liabilities=_signed(balance.total_equity_and_liabilities),
    )


def lesson(learner_id: uuid.UUID, lang: str, lesson_id: str) -> LessonView:
    lib = practice.library(lang)
    found = lib.lessons.get(lesson_id)
    if found is None:
        raise LessonError(f"Unknown lesson {lesson_id}")
    ctx = practice.recipe_context()
    example = found.exempel
    result = recipes.run(ctx, example.recept, example.datum, example.parametrar)
    document = document_view(documents.render(lib.templates[example.recept], result.figures,
                                              example.datum))
    module = lib.modules.get(found.modul)
    rules = tuple(RuleRef(r, rule_reference(lib.rules[r]), lib.rules[r].titel)
                  for r in found.regler if r in lib.rules)
    return LessonView(
        lesson_id=found.id, module_id=found.modul,
        module_title=module.titel if module else found.modul, title=found.titel,
        vad=found.vad, varfor=found.varfor, hur=found.hur, nar=found.nar,
        simplification=found.forenkling, rules=rules,
        example=_example(ctx.chart, result.voucher, example.text, document),
        exercise_ids=tuple(e.id for e in found.ovningar),
        check_ids=tuple(e.id for e in found.kontroll),
        done=found.id in _done_lessons(learner_id, [found]),
    )
