"""Practice use cases: pick an exercise, grade an answer, store the progress.

``next_exercise`` returns an exercise instance identified by exercise id
and seed; ``submit`` regenerates the same instance from them, grades the
answer and, in one transaction, stores the attempt, updates the skill state
and the svit, and returns the feedback with XP. Only the first attempt on an
instance counts for mastery and XP: the feedback after it shows the solution.

Content with status utkast is shown only when the environment variable
RA_SHOW_DRAFTS is "1" (for the owner's review, never in production).
"""

import datetime as dt
import os
import random
import re
import secrets
import uuid
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from functools import lru_cache
from zoneinfo import ZoneInfo

from ra.core.money import Money, MoneyParseError
from ra.core.reconciliation import StatementLine
from ra.core.voucher import Side, VoucherLine
from ra.learning import (
    avstamning,
    documents,
    feedback,
    gamification,
    hitta_felet,
    mastery,
    recipes,
)
from ra.learning.gamification import XP_BY_DIFFICULTY
from ra.learning.grading import (
    Grade,
    grade_amount,
    grade_choice,
    grade_classification,
    grade_kontering,
)
from ra.learning.loader import ContentLibrary, load_content
from ra.learning.schemas import Exercise, FeedbackTexts
from ra.paths import content_root
from ra.services import progress as progress_service
from ra.services.formatting import format_date, format_ore
from ra.services.views import (
    AccountOption,
    AvstamningInput,
    ExerciseView,
    InputProblem,
    RowInput,
    SkillChoice,
    SkillView,
    StatementLineView,
    SubmitResult,
    VoucherView,
    document_view,
    feedback_view,
    voucher_view,
)
from ra.storage import queries
from ra.storage.db import new_session
from ra.storage.models import SkillState

SHOW_DRAFTS_ENV = "RA_SHOW_DRAFTS"
TIMEZONE = ZoneInfo("Europe/Stockholm")
CONTEXT = "ovning"
SEED_LIMIT = 2**31
DIFFICULTIES = ("grund", "medel", "avancerad")
ACCOUNT_LABEL = re.compile(r"^\s*(\d{4})\b")

Answer = Sequence[RowInput] | AvstamningInput | str | Mapping[str, str] | int | None


class PracticeError(LookupError):
    """Unknown exercise or skill."""


def show_drafts() -> bool:
    return os.environ.get(SHOW_DRAFTS_ENV) == "1"


@lru_cache(maxsize=1)
def _context() -> recipes.RecipeContext:
    return recipes.load_context(content_root())


@lru_cache(maxsize=4)
def _library(lang: str, drafts: bool) -> ContentLibrary:
    return load_content(content_root(), lang, include_drafts=drafts)


def library(lang: str) -> ContentLibrary:
    return _library(lang, show_drafts())


def today() -> dt.date:
    return dt.datetime.now(TIMEZONE).date()


def account_options() -> tuple[AccountOption, ...]:
    """Every account in the kontoplan as "1930 Företagskonto", for search by number or name."""
    chart = _context().chart
    return tuple(AccountOption(n, f"{n} {chart[n].name}") for n in chart)


def available_skills(lang: str) -> tuple[SkillChoice, ...]:
    """Skills that have published övningar, with the difficulties on offer."""
    lib = library(lang)
    choices = []
    for skill in lib.skills.values():
        found = {e.niva for e in lib.practice_exercises(skill.id)}
        if found:
            levels = tuple(d for d in DIFFICULTIES if d in found)
            choices.append(SkillChoice(skill.id, skill.namn, levels))
    return tuple(choices)


@dataclass(frozen=True)
class Instance:
    """One exercise with its seed and what was generated for it: recipe figures and key,
    a planted error (hitta felet) or a month to reconcile (avstämning)."""

    exercise: Exercise
    seed: int
    generated: recipes.Generated | None = None
    planted: hitta_felet.PlantedError | None = None
    task: avstamning.ReconciliationTask | None = None


def instance(lang: str, exercise_id: str, seed: int) -> Instance:
    exercise = library(lang).exercises.get(exercise_id)
    if exercise is None:
        raise PracticeError(f"Unknown exercise {exercise_id}")
    ctx = _context()
    if exercise.typ == "avstamning":
        return Instance(exercise, seed, task=avstamning.generate(ctx, seed))
    generated = (recipes.generate(ctx, exercise.recept, seed, exercise.parametrar)
                 if exercise.recept else None)
    planted = (hitta_felet.plant(ctx.chart, generated.result.voucher, seed)
               if generated is not None and exercise.typ == "hitta_felet" else None)
    return Instance(exercise, seed, generated, planted)


def _statement_views(lines: Sequence[StatementLine]) -> tuple[StatementLineView, ...]:
    return tuple(StatementLineView(i, format_date(ln.date), ln.text, format_ore(ln.amount.ore))
                 for i, ln in enumerate(lines))


def _exercise_view(lang: str, inst: Instance) -> ExerciseView:
    exercise, lib, chart = inst.exercise, library(lang), _context().chart
    document = None
    if inst.generated is not None:
        template = lib.templates[exercise.dokument or exercise.recept or ""]
        hidden = {exercise.svar} if exercise.svar else set()
        document = document_view(documents.render(template, inst.generated.result.figures,
                                                  inst.generated.on_date, hidden))
    return ExerciseView(
        exercise_id=exercise.id, seed=inst.seed, typ=exercise.typ, skill_id=exercise.kompetens,
        difficulty=exercise.niva, instruction=exercise.uppgift or "", hint=exercise.tips,
        document=document, question=exercise.fraga or "", options=exercise.alternativ,
        categories=exercise.kategorier, items=tuple(p.text for p in exercise.poster),
        booked=voucher_view(chart, inst.planted.booked.lines) if inst.planted else None,
        statement=_statement_views(inst.task.statement) if inst.task else (),
        ledger=_statement_views(inst.task.ledger) if inst.task else (),
    )


def exercise_view(lang: str, exercise_id: str, seed: int) -> ExerciseView:
    """The same exercise instance again, for example after a rerun of the page."""
    return _exercise_view(lang, instance(lang, exercise_id, seed))


def next_exercise(learner_id: uuid.UUID, skill_id: str, difficulty: str, lang: str,
                  seed: int | None = None) -> ExerciseView | None:
    """A new exercise instance for the skill, preferring exercises the learner has not done."""
    candidates = library(lang).practice_exercises(skill_id, difficulty)
    if not candidates:
        return None
    with new_session() as session:
        done = queries.attempted_items(session, learner_id, skill_id)
    fresh = [e for e in candidates if e.id not in done] or list(candidates)
    chosen_seed = secrets.randbelow(SEED_LIMIT) if seed is None else seed
    exercise = random.Random(chosen_seed).choice(fresh)
    return _exercise_view(lang, instance(lang, exercise.id, chosen_seed))


def _progress(row: SkillState | None) -> mastery.SkillProgress:
    if row is None:
        return mastery.SkillProgress()
    return mastery.SkillProgress(
        state=mastery.SkillLevel(row.state), total=row.total, recent=tuple(row.recent),
        kontering_passed=row.kontering_passed, repetitions_ok=row.repetitions_ok,
        due_on=row.due_on)


def _skill_view(lang: str, skill_id: str, progress: mastery.SkillProgress) -> SkillView:
    skill = library(lang).skills.get(skill_id)
    share = progress.recent_share
    return SkillView(
        skill_id=skill_id, name=skill.namn if skill else skill_id, state=progress.state,
        total=progress.total,
        recent_percent=round(share * 100) if progress.recent else None,
        due_on=format_date(progress.due_on) if progress.due_on else None)


def skill_view(learner_id: uuid.UUID, skill_id: str, lang: str) -> SkillView:
    with new_session() as session:
        row = queries.get_skill_state(session, learner_id, skill_id)
        return _skill_view(lang, skill_id, _progress(row))


def parse_rows(
    rows: Sequence[RowInput],
) -> tuple[tuple[VoucherLine, ...], tuple[InputProblem, ...]]:
    """Grid rows to kontering lines; blank rows are skipped, problems collected."""
    lines: list[VoucherLine] = []
    problems: list[InputProblem] = []
    for row in rows:
        debet, kredit = (row.debet or "").strip(), (row.kredit or "").strip()
        match = ACCOUNT_LABEL.match(row.account or "")
        if not debet and not kredit:
            continue
        if match is None:
            problems.append(InputProblem.KONTO_SAKNAS)
            continue
        if debet and kredit:
            problems.append(InputProblem.BADA_SIDOR)
            continue
        try:
            amount = Money.parse(debet or kredit)
        except MoneyParseError:
            problems.append(InputProblem.BELOPP_OLASLIGT)
            continue
        if amount.ore <= 0:
            problems.append(InputProblem.BELOPP_OLASLIGT)
            continue
        lines.append(VoucherLine(int(match.group(1)), Side.DEBET if debet else Side.KREDIT,
                                 amount))
    if not lines and not problems:
        problems.append(InputProblem.TOMT_SVAR)
    return tuple(lines), tuple(dict.fromkeys(problems))


def totals(rows: Sequence[RowInput]) -> VoucherView:
    """Running totals and balance for the rows that can be read so far."""
    lines, _ = parse_rows(rows)
    return voucher_view(_context().chart, lines)


@dataclass(frozen=True)
class Graded:
    grade: Grade
    treatment: feedback.Treatment


def _texts(lang: str) -> FeedbackTexts:
    texts = library(lang).feedback
    if texts is None:
        raise PracticeError("content/feedback.yaml is missing")
    return texts


GradeOutcome = Graded | tuple[InputProblem, ...]


def _rows(answer: Answer) -> list[RowInput]:
    rows = answer.rows if isinstance(answer, AvstamningInput) else answer
    if isinstance(rows, str) or not isinstance(rows, Sequence):
        return []
    return [r for r in rows if isinstance(r, RowInput)]


def _grade_kontering(texts: FeedbackTexts, inst: Instance, answer: Answer) -> GradeOutcome:
    chart, result = _context().chart, _required(inst.generated, inst).result
    lines, problems = parse_rows(_rows(answer))
    if problems:
        return problems
    return Graded(grade_kontering(chart, lines, result),
                  feedback.kontering_treatment(texts, chart, result))


def _grade_berakning(texts: FeedbackTexts, inst: Instance, answer: Answer) -> GradeOutcome:
    result, svar = _required(inst.generated, inst).result, inst.exercise.svar or ""
    expected = result.figures.get(svar)
    if not isinstance(expected, Money):
        raise PracticeError(f"{inst.exercise.id}: svar {svar} is not an amount")
    try:
        given = Money.parse(answer.strip() if isinstance(answer, str) else "")
    except MoneyParseError:
        return (InputProblem.BELOPP_OLASLIGT,)
    return Graded(grade_amount(given, expected, result.figures, svar),
                  feedback.amount_treatment(texts, expected))


def _grade_klassificering(texts: FeedbackTexts, inst: Instance, answer: Answer) -> GradeOutcome:
    expected = {p.text: p.kategori for p in inst.exercise.poster}
    given = dict(answer) if isinstance(answer, Mapping) else {}
    return Graded(grade_classification(given, expected),
                  feedback.classification_treatment(texts, expected))


def _grade_resonemang(texts: FeedbackTexts, inst: Instance, answer: Answer) -> GradeOutcome:
    right = _required(inst.exercise.ratt, inst)
    return Graded(grade_choice(answer if isinstance(answer, int) else None, right),
                  feedback.choice_treatment(texts, inst.exercise.alternativ[right]))


def _grade_hitta_felet(texts: FeedbackTexts, inst: Instance, answer: Answer) -> GradeOutcome:
    chart, planted = _context().chart, _required(inst.planted, inst)
    lines, problems = parse_rows(_rows(answer))
    if problems:
        return problems
    return Graded(hitta_felet.grade_correction(chart, planted, lines),
                  feedback.correction_treatment(
                      texts, hitta_felet.suggested_correction(chart, planted)))


def _grade_avstamning(texts: FeedbackTexts, inst: Instance, answer: Answer) -> GradeOutcome:
    chart, task = _context().chart, _required(inst.task, inst)
    lines, problems = parse_rows(_rows(answer))
    if problems:
        return problems
    marked = answer.marked if isinstance(answer, AvstamningInput) else frozenset()
    result = avstamning.grade(chart, task, marked, lines)
    differing = tuple(f"{format_date(ln.date)}, {ln.text}, {format_ore(ln.amount.ore)}"
                      for i, ln in enumerate(task.statement) if i in task.differing)
    grade = Grade(True) if result.correct else Grade(False, result.booking.codes)
    return Graded(grade, feedback.reconciliation_treatment(texts, task.key.lines, differing))


GRADERS = {
    "kontering": _grade_kontering, "berakning": _grade_berakning,
    "klassificering": _grade_klassificering, "resonemang": _grade_resonemang,
    "hitta_felet": _grade_hitta_felet, "avstamning": _grade_avstamning,
}


def _required[T](value: T | None, inst: Instance) -> T:
    if value is None:
        raise PracticeError(f"{inst.exercise.id}: the exercise lacks what its type needs")
    return value


def _grade(lang: str, inst: Instance, answer: Answer) -> GradeOutcome:
    grader = GRADERS.get(inst.exercise.typ)
    if grader is None:
        raise PracticeError(f"Exercise type {inst.exercise.typ} cannot be graded")
    return grader(_texts(lang), inst, answer)


def submit(learner_id: uuid.UUID, exercise_id: str, seed: int, answer: Answer,
           hints_used: int, lang: str) -> SubmitResult:
    """Grade, store the attempt, update skill state and svit; one transaction."""
    inst = instance(lang, exercise_id, seed)
    graded = _grade(lang, inst, answer)
    if not isinstance(graded, Graded):
        return SubmitResult(problems=graded)
    grade = graded.grade
    exercise, lib, on_date = inst.exercise, library(lang), today()
    built = feedback.build(grade, exercise, lib.rules[exercise.regel], _texts(lang),
                           graded.treatment)
    with new_session() as session, session.begin():
        attempt_no = queries.count_attempts(session, learner_id, exercise.id, seed) + 1
        earlier = progress_service.correct_today(session, learner_id, exercise.id, on_date,
                                                 TIMEZONE)
        xp = gamification.xp_for(exercise.niva, grade.correct, attempt_no, hints_used, earlier)
        xp_capped = grade.correct and attempt_no == 1 and xp < XP_BY_DIFFICULTY[exercise.niva]
        progress = _progress(queries.get_skill_state(session, learner_id, exercise.kompetens))
        if attempt_no == 1:
            progress = mastery.update(progress, mastery.Outcome(
                grade.correct, hints_used, exercise.typ, on_date))
            queries.save_skill_state(session, learner_id, exercise.kompetens, {
                "state": progress.state.value, "total": progress.total,
                "recent": list(progress.recent), "kontering_passed": progress.kontering_passed,
                "repetitions_ok": progress.repetitions_ok, "due_on": progress.due_on})
        progress_service.record_attempt(session, learner_id, {
            "item_id": exercise.id, "skill_id": exercise.kompetens, "context": CONTEXT,
            "difficulty": exercise.niva, "seed": seed, "is_correct": grade.correct,
            "attempt_no": attempt_no, "hints_used": hints_used,
            "error_codes": [c.value for c in grade.codes], "xp": xp}, on_date)
        total_xp = queries.total_xp(session, learner_id)
    return SubmitResult(
        feedback=feedback_view(_context().chart, built), xp=xp, total_xp=total_xp,
        attempt_no=attempt_no, xp_capped=xp_capped,
        skill=_skill_view(lang, exercise.kompetens, progress))

