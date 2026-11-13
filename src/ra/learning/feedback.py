"""Återkoppling in five parts: vad som blev fel, varför, rätt hantering, regel, tips.

Parts 1 and 2 come from the most telling error code (texts in
content/feedback.yaml); without a matching code the general text is used,
so a wrong answer always gets all five parts. Part 3 is built from the
engine's key, part 4 from the exercise's rule entry and part 5 from its tip.
Accepted alternative accounts are named in part 3 for right and wrong answers.
"""

from collections.abc import Mapping
from dataclasses import dataclass

from ra.core.chart import Chart
from ra.core.formatting import format_ore
from ra.core.money import Money
from ra.core.voucher import VoucherLine
from ra.learning.grading import Grade
from ra.learning.recipes import RecipeResult
from ra.learning.schemas import Exercise, FeedbackTexts, Rule


@dataclass(frozen=True)
class Treatment:
    """Rätt hantering: a sentence, the correct rows when there are any, and notes."""

    text: str
    lines: tuple[VoucherLine, ...] = ()
    notes: tuple[str, ...] = ()


@dataclass(frozen=True)
class RuleReference:
    """Regel med källa: law or norm, chapter and section, title and the official link."""

    title: str
    reference: str
    source_url: str


@dataclass(frozen=True)
class Feedback:
    """The five parts in fixed order, plus the heading and the codes behind them."""

    correct: bool
    heading: str
    what: str
    why: str
    treatment: Treatment
    rule: RuleReference
    tip: str
    codes: tuple[str, ...] = ()


def _account_label(chart: Chart, number: int) -> str:
    return f"{number} {chart[number].name}" if number in chart else str(number)


def kontering_treatment(texts: FeedbackTexts, chart: Chart, key: RecipeResult) -> Treatment:
    """The key verifikation and a note for every accepted alternative account."""
    notes = tuple(
        texts.texter.alternativt_konto.format(alternativ=_account_label(chart, alternative),
                                              konto=_account_label(chart, account))
        for account, accepted in key.alternatives.items() for alternative in sorted(accepted)
    )
    return Treatment(texts.texter.ratt_kontering, key.voucher.lines, notes)


def amount_treatment(texts: FeedbackTexts, expected: Money) -> Treatment:
    return Treatment(texts.texter.ratt_belopp.format(belopp=format_ore(expected.ore)))


def choice_treatment(texts: FeedbackTexts, alternative: str) -> Treatment:
    return Treatment(texts.texter.ratt_val.format(svar=alternative))


def classification_treatment(texts: FeedbackTexts, expected: Mapping[str, str]) -> Treatment:
    notes = tuple(f"{item}: {category}" for item, category in expected.items())
    return Treatment(texts.texter.ratt_klassificering, notes=notes)


def rule_reference(rule: Rule) -> RuleReference:
    return RuleReference(title=rule.titel, reference=f"{rule.namn} {rule.lagrum}",
                         source_url=rule.kalla)


def build(grade: Grade, exercise: Exercise, rule: Rule, texts: FeedbackTexts,
          treatment: Treatment) -> Feedback:
    """Assemble the feedback for one graded answer."""
    reference = rule_reference(rule)
    codes = tuple(code.value for code in grade.codes)
    if grade.correct:
        return Feedback(True, texts.texter.ratt, "", "", treatment, reference, exercise.tips)
    main = texts.koder.get(codes[0]) if codes else None
    entry = main or texts.allmant
    what = entry.vad
    others = [texts.koder[c].rubrik for c in codes[1:] if c in texts.koder]
    if main is not None and others:
        what = f"{what} {texts.texter.fler_fel.format(fel=', '.join(others).lower())}"
    return Feedback(False, entry.rubrik, what, entry.varfor, treatment, reference,
                    exercise.tips, codes)
