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
from pathlib import Path
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from ra.core.money import Money, MoneyParseError
from ra.core.voucher import Side, VoucherLine
from ra.learning import documents, feedback, gamification, mastery, recipes
from ra.learning.grading import (
    Grade,
    grade_amount,
    grade_choice,
    grade_classification,
    grade_kontering,
)
from ra.learning.loader import ContentLibrary, load_content
from ra.learning.schemas import Exercise, FeedbackTexts
from ra.services.formatting import format_date
from ra.services.views import (
    AccountOption,
    ExerciseView,
    InputProblem,
    RowInput,
    SkillChoice,
    SkillView,
    SubmitResult,
    VoucherView,
    document_view,
    feedback_view,
    voucher_view,
)
from ra.storage import queries
from ra.storage.db import new_session
from ra.storage.models import SkillState

CONTENT_ROOT = Path(__file__).resolve().parents[3] / "content"
SHOW_DRAFTS_ENV = "RA_SHOW_DRAFTS"
TIMEZONE = ZoneInfo("Europe/Stockholm")
CONTEXT = "ovning"
SEED_LIMIT = 2**31
DIFFICULTIES = ("grund", "medel", "avancerad")
ACCOUNT_LABEL = re.compile(r"^\s*(\d{4})\b")

Answer = Sequence[RowInput] | str | Mapping[str, str] | int | None


class PracticeError(LookupError):
    """Unknown exercise or skill."""


def show_drafts() -> bool:
    return os.environ.get(SHOW_DRAFTS_ENV) == "1"


@lru_cache(maxsize=1)
def _context() -> recipes.RecipeContext:
    return recipes.load_context(CONTENT_ROOT)


@lru_cache(maxsize=4)
def _library(lang: str, drafts: bool) -> ContentLibrary:
    return load_content(CONTENT_ROOT, lang, include_drafts=drafts)


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
    """One exercise with its seed and, when it has a recipe, the generated figures and key."""

    exercise: Exercise
    seed: int
    generated: recipes.Generated | None


def instance(lang: str, exercise_id: str, seed: int) -> Instance:
    exercise = library(lang).exercises.get(exercise_id)
    if exercise is None:
        raise PracticeError(f"Unknown exercise {exercise_id}")
    generated = (recipes.generate(_context(), exercise.recept, seed, exercise.parametrar)
                 if exercise.recept else None)
    return Instance(exercise, seed, generated)


def _exercise_view(lang: str, inst: Instance) -> ExerciseView:
    exercise, lib = inst.exercise, library(lang)
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
    )


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


def _grade(lang: str, inst: Instance, answer: Answer) -> Graded | tuple[InputProblem, ...]:
    exercise, texts, chart = inst.exercise, _texts(lang), _context().chart
    result = inst.generated.result if inst.generated else None
    if exercise.typ == "kontering" and result is not None and isinstance(answer, Sequence):
        lines, problems = parse_rows([r for r in answer if isinstance(r, RowInput)])
        if problems:
            return problems
        return Graded(grade_kontering(chart, lines, result),
                      feedback.kontering_treatment(texts, chart, result))
    if exercise.typ == "berakning" and result is not None and exercise.svar:
        expected = result.figures.get(exercise.svar)
        if not isinstance(expected, Money):
            raise PracticeError(f"{exercise.id}: svar {exercise.svar} is not an amount")
        try:
            given = Money.parse(answer.strip() if isinstance(answer, str) else "")
        except MoneyParseError:
            return (InputProblem.BELOPP_OLASLIGT,)
        return Graded(grade_amount(given, expected, result.figures, exercise.svar),
                      feedback.amount_treatment(texts, expected))
    if exercise.typ == "klassificering":
        expected_map = {p.text: p.kategori for p in exercise.poster}
        given_map = dict(answer) if isinstance(answer, Mapping) else {}
        return Graded(grade_classification(given_map, expected_map),
                      feedback.classification_treatment(texts, expected_map))
    if exercise.typ == "resonemang" and exercise.ratt is not None:
        choice = answer if isinstance(answer, int) else None
        return Graded(grade_choice(choice, exercise.ratt),
                      feedback.choice_treatment(texts, exercise.alternativ[exercise.ratt]))
    raise PracticeError(f"Exercise type {exercise.typ} cannot be graded here")


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
        xp = gamification.xp_for(exercise.niva, grade.correct, attempt_no, hints_used)
        progress = _progress(queries.get_skill_state(session, learner_id, exercise.kompetens))
        if attempt_no == 1:
            progress = mastery.update(progress, mastery.Outcome(
                grade.correct, hints_used, exercise.typ, on_date))
            queries.save_skill_state(session, learner_id, exercise.kompetens, {
                "state": progress.state.value, "total": progress.total,
                "recent": list(progress.recent), "kontering_passed": progress.kontering_passed,
                "repetitions_ok": progress.repetitions_ok, "due_on": progress.due_on})
        queries.add_attempt(session, {
            "learner_id": learner_id, "item_id": exercise.id, "skill_id": exercise.kompetens,
            "context": CONTEXT, "difficulty": exercise.niva, "seed": seed,
            "is_correct": grade.correct, "attempt_no": attempt_no, "hints_used": hints_used,
            "error_codes": [c.value for c in grade.codes], "xp": xp})
        _update_streak(session, learner_id, on_date)
        total_xp = queries.total_xp(session, learner_id)
    return SubmitResult(
        feedback=feedback_view(_context().chart, built), xp=xp, total_xp=total_xp,
        attempt_no=attempt_no, skill=_skill_view(lang, exercise.kompetens, progress))


def _update_streak(session: Session, learner_id: uuid.UUID, on_date: dt.date) -> None:
    learner = queries.get_learner(session, learner_id)
    if learner is None:
        raise PracticeError(f"Unknown learner {learner_id}")
    streak = gamification.update_streak(gamification.Streak(
        learner.streak_current, learner.streak_longest, learner.last_active_on), on_date)
    queries.save_streak(session, learner_id, streak.current, streak.longest,
                        streak.last_active_on)

