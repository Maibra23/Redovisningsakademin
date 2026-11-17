"""Prov (PRD sections 7 and 12): the list, an exam in progress and its submission.

An exam is drawn by ``learning.exams`` from its seed, so the page keeps only
the exam id and the seed. Every item is graded at submission with the five part
feedback; the result is stored in exam_result. A passed exam also counts as
attempts for mastery (context prov), in the same transaction. Submitting the
same exam and seed again stores nothing new.
"""

import secrets
import uuid
from collections.abc import Sequence

from ra.learning import exams
from ra.learning.loader import natural_key
from ra.learning.schemas import Exam
from ra.services import practice
from ra.services.views import (
    ExamItemResultView,
    ExamResultView,
    ExamSummaryView,
    ExamView,
)
from ra.storage import queries
from ra.storage.db import new_session

CONTEXT = "prov"
FINAL_EXAM = "prov.slutprov"
FINAL_BADGE = "Godkänt slutprov"


class ExamError(LookupError):
    """Unknown exam, or answers that do not match its items."""


def _exam(lang: str, exam_id: str) -> Exam:
    exam = practice.library(lang).exams.get(exam_id)
    if exam is None:
        raise ExamError(f"Unknown exam {exam_id}")
    return exam


def _order(exam: Exam) -> tuple[int, tuple[tuple[int, int | str], ...]]:
    """Module exams in module order, the slutprov last."""
    return (exam.modul is None, natural_key(exam.modul or exam.id))


def exam_list(learner_id: uuid.UUID, lang: str) -> tuple[ExamSummaryView, ...]:
    with new_session() as session:
        results = queries.exam_results(session, learner_id)
    views = []
    for exam in sorted(practice.library(lang).exams.values(), key=_order):
        own = [r for r in results if r.exam_id == exam.id]
        best = max(own, key=lambda r: r.score, default=None)
        score = (exams.ExamScore(best.score, exam.antal, exam.godkant_procent)
                 if best is not None else None)
        views.append(ExamSummaryView(
            exam.id, exam.titel, exam.antal, exam.godkant_procent,
            score.correct if score else None, score.percent if score else None,
            any(r.passed for r in own), len(own)))
    return tuple(views)


def _items(lang: str, exam: Exam, seed: int) -> tuple[exams.ExamItem, ...]:
    return exams.draw(exam, practice.library(lang).exercises, seed)


def exam_view(lang: str, exam_id: str, seed: int) -> ExamView:
    exam = _exam(lang, exam_id)
    views = tuple(practice.exercise_view(lang, item.exercise_id, item.seed)
                  for item in _items(lang, exam, seed))
    return ExamView(exam.id, seed, exam.titel, exam.godkant_procent, views)


def start(lang: str, exam_id: str) -> ExamView:
    """A new exam with a new seed."""
    return exam_view(lang, exam_id, secrets.randbelow(exams.SEED_LIMIT))


def submit(learner_id: uuid.UUID, lang: str, exam_id: str, seed: int,
           answers: Sequence[practice.Answer]) -> ExamResultView:
    """Grade every item, store the result and, when passed, the attempts; one transaction."""
    exam = _exam(lang, exam_id)
    items = _items(lang, exam, seed)
    if len(answers) != len(items):
        raise ExamError(f"{exam_id}: {len(answers)} answers for {len(items)} items")
    graded = [practice.grade_item(lang, item.exercise_id, item.seed, answer)
              for item, answer in zip(items, answers, strict=True)]
    score = exams.score(exam, (g.grade.correct for g in graded))
    with new_session() as session, session.begin():
        if not queries.has_exam_result(session, learner_id, exam.id, seed):
            queries.add_exam_result(session, {
                "learner_id": learner_id, "exam_id": exam.id, "seed": seed,
                "score": score.correct, "passed": score.passed})
            if score.passed:
                on_date = practice.today()
                for item, g in zip(items, graded, strict=True):
                    practice.record_graded(session, learner_id, g.exercise, item.seed, g.grade,
                                           0, CONTEXT, on_date)
    return ExamResultView(
        exam_id=exam.id, title=exam.titel, correct=score.correct, total=score.total,
        percent=score.percent, pass_percent=exam.godkant_procent, passed=score.passed,
        items=tuple(ExamItemResultView(i, g.grade.correct, g.feedback, g.problems)
                    for i, g in enumerate(graded, start=1)),
        badge=FINAL_BADGE if score.passed and exam.id == FINAL_EXAM else None)
