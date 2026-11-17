"""Prov: draw the items by seed and score them at submission (PRD sections 7 and 12).

The items are spread over the skills of the pool: each skill's exercises are
shuffled by the seed and the skills take turns, so a module exam of eight
items covers every skill of the module and the slutprov covers all nineteen.
Each item gets its own seed for the recipe, also from the exam's seed, so the
same exam seed always gives the same items with the same figures.
"""

import random
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass

from ra.learning.loader import exam_pool
from ra.learning.schemas import Exam, Exercise

SEED_LIMIT = 2**31


@dataclass(frozen=True)
class ExamItem:
    exercise_id: str
    seed: int


@dataclass(frozen=True)
class ExamScore:
    """Right items out of all; passed when the share reaches the pass mark exactly or above."""

    correct: int
    total: int
    pass_percent: int

    @property
    def passed(self) -> bool:
        return self.correct * 100 >= self.pass_percent * self.total

    @property
    def percent(self) -> int:
        """The share right in whole percent, rounded half up."""
        return (self.correct * 200 + self.total) // (2 * self.total)


def draw(exam: Exam, exercises: Mapping[str, Exercise], seed: int) -> tuple[ExamItem, ...]:
    """``exam.antal`` items from the exam's pool, the skills taking turns."""
    rng = random.Random(f"prov:{exam.id}:{seed}")
    groups: dict[str, list[Exercise]] = {}
    for exercise in exam_pool(exam, exercises):
        groups.setdefault(exercise.kompetens, []).append(exercise)
    for group in groups.values():
        rng.shuffle(group)
    queues = [groups[skill] for skill in sorted(groups)]
    rng.shuffle(queues)
    chosen: list[Exercise] = []
    while len(chosen) < exam.antal and any(queues):
        for queue in queues:
            if queue and len(chosen) < exam.antal:
                chosen.append(queue.pop())
    rng.shuffle(chosen)
    return tuple(ExamItem(e.id, rng.randrange(SEED_LIMIT)) for e in chosen)


def score(exam: Exam, results: Iterable[bool]) -> ExamScore:
    marks: Sequence[bool] = tuple(results)
    return ExamScore(sum(marks), len(marks), exam.godkant_procent)
