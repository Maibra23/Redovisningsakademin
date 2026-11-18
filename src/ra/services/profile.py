"""Översikt, Kompetensprofil, Prestationer and Dagens utmaning (PRD sections 6, 7 and 9).

Everything here is read from the stored attempts, skill states, svit and exam
results; nothing is written. The recommended next step follows a fixed order:
due repetitions, then the weakest skill still at Övar, then the next lesson that
is not done, then the simulator.
"""

import datetime as dt
import uuid
from collections import Counter

from ra.core.formatting import MONTHS
from ra.learning import badges, gamification
from ra.learning import exams as exam_logic
from ra.learning.loader import natural_key
from ra.learning.mastery import SkillLevel, SkillProgress
from ra.services import lessons, practice, simulator
from ra.services.formatting import format_date
from ra.services.views import (
    AchievementsView,
    ActivityDayView,
    BadgeView,
    ChallengeItemView,
    ChallengeView,
    LevelRowView,
    LevelView,
    NextStep,
    NextStepView,
    OverviewView,
    PassedExamView,
    ProfileSkillView,
    ProfileView,
    RoleProgressView,
    SkillView,
)
from ra.storage import queries
from ra.storage.db import new_session

CHALLENGE_CONTEXT = "utmaning"
SIMULATOR_ITEM_PREFIX = "sim."
ACTIVITY_DAYS = 30
WEAKEST_COUNT = 3
COMPETENT = (SkillLevel.KOMPETENT, SkillLevel.BEFAST)


def _local_date(moment: dt.datetime) -> dt.date:
    """Stored times are UTC; SQLite gives them back without a zone."""
    aware = moment if moment.tzinfo else moment.replace(tzinfo=dt.UTC)
    return aware.astimezone(practice.TIMEZONE).date()


def _progress(learner_id: uuid.UUID) -> dict[str, SkillProgress]:
    with new_session() as session:
        return {row.skill_id: practice.progress_of(row)
                for row in queries.skill_states(session, learner_id)}


def _competent(progress: dict[str, SkillProgress]) -> set[str]:
    return {skill for skill, p in progress.items() if p.state in COMPETENT}


def _roles(lang: str) -> dict[str, set[str]]:
    return {role.id: set(role.kompetenser) for role in practice.library(lang).roles}


def _level(lang: str, xp: int, competent: set[str]) -> LevelView:
    roles = _roles(lang)
    current = gamification.level(xp, competent, roles)
    index = gamification.LEVELS.index(current)
    if index + 1 == len(gamification.LEVELS):
        return LevelView(current.name, xp, None, None, None)
    following = gamification.LEVELS[index + 1]
    held_back = (following.role is not None and xp >= following.min_xp
                 and not roles.get(following.role, set()) <= competent)
    role_name = next((r.namn for r in practice.library(lang).roles if r.id == following.role),
                     None)
    return LevelView(current.name, xp, following.name, max(0, following.min_xp - xp),
                     role_name if held_back else None)


def _weakest(lang: str, progress: dict[str, SkillProgress]) -> tuple[SkillView, ...]:
    """Practised skills below Kompetent with the lowest share right lately; fewer attempts
    first on a tie."""
    practised = [(skill, p) for skill, p in progress.items()
                 if p.recent and p.state not in COMPETENT]
    practised.sort(key=lambda item: (item[1].recent_share, item[1].total, item[0]))
    return tuple(practice.skill_view_of(lang, skill, p)
                 for skill, p in practised[:WEAKEST_COUNT])


def _next_step(learner_id: uuid.UUID, lang: str, due: tuple[SkillView, ...],
               weakest: tuple[SkillView, ...]) -> NextStepView:
    if due:
        return NextStepView(NextStep.REPETITION, due[0].skill_id, due[0].name)
    practised = {choice.skill_id for choice in practice.available_skills(lang)}
    weak = next((s for s in weakest if s.state is SkillLevel.OVAR and s.skill_id in practised),
                None)
    if weak is not None:
        return NextStepView(NextStep.SKILL, weak.skill_id, weak.name)
    for module in lessons.modules(learner_id, lang):
        lesson = next((lesson for lesson in module.lessons if not lesson.done), None)
        if lesson is not None:
            return NextStepView(NextStep.LESSON, lesson.lesson_id, lesson.title)
    return NextStepView(NextStep.SIMULATOR)


def _activity(learner_id: uuid.UUID) -> tuple[ActivityDayView, ...]:
    today = practice.today()
    first = today - dt.timedelta(days=ACTIVITY_DAYS - 1)
    since = dt.datetime.combine(first, dt.time.min, tzinfo=practice.TIMEZONE)
    with new_session() as session:
        rows = queries.attempts_since(session, learner_id, since.astimezone(dt.UTC))
    right = Counter(_local_date(at) for at, ok in rows if ok)
    wrong = Counter(_local_date(at) for at, ok in rows if not ok)
    days = (first + dt.timedelta(days=i) for i in range(ACTIVITY_DAYS))
    return tuple(ActivityDayView(day, f"{day.day} {MONTHS[day.month - 1][:3]}", right[day],
                                 wrong[day]) for day in days)


def overview(learner_id: uuid.UUID, lang: str) -> OverviewView:
    progress = _progress(learner_id)
    due = practice.due_skills(learner_id, lang)
    weakest = _weakest(lang, progress)
    with new_session() as session:
        learner = queries.get_learner(session, learner_id)
        xp = queries.total_xp(session, learner_id)
    streak = learner.streak_current if learner else 0
    longest = learner.streak_longest if learner else 0
    return OverviewView(
        has_history=any(p.total for p in progress.values()),
        next_step=_next_step(learner_id, lang, due, weakest),
        due_count=len(due), streak=streak, longest_streak=longest,
        level=_level(lang, xp, _competent(progress)), weakest=weakest,
        activity=_activity(learner_id))


def _passed_exams(learner_id: uuid.UUID, lang: str) -> tuple[PassedExamView, ...]:
    library = practice.library(lang)
    with new_session() as session:
        results = queries.exam_results(session, learner_id)
    views = []
    for exam_id in sorted({r.exam_id for r in results if r.passed}, key=natural_key):
        exam = library.exams.get(exam_id)
        if exam is None:
            continue
        passed = [r for r in results if r.exam_id == exam_id and r.passed]
        best = max(passed, key=lambda r: r.score)
        score = exam_logic.ExamScore(best.score, exam.antal, exam.godkant_procent)
        views.append(PassedExamView(exam.titel, score.correct, score.total, score.percent,
                                    format_date(_local_date(passed[0].created_at))))
    return tuple(views)


def competence_profile(learner_id: uuid.UUID, lang: str) -> ProfileView:
    library = practice.library(lang)
    progress = _progress(learner_id)
    with new_session() as session:
        last = queries.last_attempt_by_skill(session, learner_id)
    skills = []
    for skill in library.skills.values():
        own = progress.get(skill.id, SkillProgress())
        view = practice.skill_view_of(lang, skill.id, own)
        module = library.modules.get(skill.modul)
        skills.append(ProfileSkillView(
            skill.id, skill.namn, module.titel if module else skill.modul, own.state,
            view.recent_percent, own.total,
            format_date(_local_date(last[skill.id])) if skill.id in last else None))
    competent = _competent(progress)
    roles = tuple(RoleProgressView(role.namn, len(set(role.kompetenser) & competent),
                                   len(role.kompetenser),
                                   tuple(s for s in role.kompetenser if s not in competent))
                  for role in library.roles)
    return ProfileView(any(p.total for p in progress.values()), tuple(skills), roles,
                       _passed_exams(learner_id, lang))


def _evidence(learner_id: uuid.UUID, lang: str) -> badges.Evidence:
    exercises = practice.library(lang).exercises
    with new_session() as session:
        right = queries.right_answers(session, learner_id)
        passed = {r.exam_id for r in queries.exam_results(session, learner_id) if r.passed}
    kontering = any(item.startswith(SIMULATOR_ITEM_PREFIX)
                    or (item in exercises and exercises[item].typ == "kontering")
                    for item, _ in right)
    return badges.Evidence(frozenset(skill for _, skill in right), kontering, frozenset(passed),
                           simulator.month_finished(learner_id))


def achievements(learner_id: uuid.UUID, lang: str) -> AchievementsView:
    """The märken, derived now from attempts, simulator verifikationer and exam results,
    and the nivåer with the learner's place among them."""
    library = practice.library(lang)
    evidence = _evidence(learner_id, lang)
    progress = _progress(learner_id)
    with new_session() as session:
        xp = queries.total_xp(session, learner_id)
    level = _level(lang, xp, _competent(progress))
    reached = next(i for i, candidate in enumerate(gamification.LEVELS)
                   if candidate.name == level.name)
    role_names = {role.id: role.namn for role in library.roles}
    return AchievementsView(
        tuple(BadgeView(b.namn, b.beskrivning, badges.earned(b, evidence))
              for b in library.badges),
        level,
        tuple(LevelRowView(lv.name, lv.min_xp, role_names.get(lv.role) if lv.role else None,
                           i <= reached) for i, lv in enumerate(gamification.LEVELS)))


def challenge(learner_id: uuid.UUID, lang: str) -> ChallengeView:
    """Dagens utmaning: the same five exercises for everyone today, and this learner's
    first answer on each."""
    library, on_date = practice.library(lang), practice.today()
    items = badges.daily_challenge(library.exercises.values(), on_date)
    with new_session() as session:
        results = [queries.first_result(session, learner_id, i.exercise_id, i.seed)
                   for i in items]
    return ChallengeView(format_date(on_date), tuple(
        ChallengeItemView(i.exercise_id, i.seed,
                          library.skills[library.exercises[i.exercise_id].kompetens].namn, right)
        for i, right in zip(items, results, strict=True)))
