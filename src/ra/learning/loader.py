"""Load content/ into one read only library, resolve references, hide drafts.

Swedish files are the source. When English is chosen, a file with the same
relative path under content/en is used instead if it exists; otherwise the
Swedish file is used. Entries with status utkast are hidden unless drafts
are asked for (the validator and local review do that).

Parsing collects every error instead of stopping at the first, so the
validator can report them all at once.
"""

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from types import MappingProxyType
from typing import Any

import yaml
from pydantic import BaseModel, ValidationError

from ra.learning.schemas import (
    DocumentTemplate,
    Exam,
    Exercise,
    FeedbackTexts,
    Glossary,
    GlossaryTerm,
    Lesson,
    RoleTarget,
    Rule,
    RuleFile,
    Skill,
    SkillCatalogue,
    TemplateFile,
)

ENGLISH_DIR = "en"
SKILLS_FILE = "kompetenser.yaml"
TEMPLATES_FILE = "dokumentmallar.yaml"
GLOSSARY_FILE = "ordlista.yaml"
FEEDBACK_FILE = "feedback.yaml"
RULES_DIR = "regler"
LESSONS_DIR = "moduler"
EXAMS_DIR = "prov"
DRAFT = "utkast"

class ContentError(ValueError):
    """Content files are invalid; ``errors`` lists every problem found."""

    def __init__(self, errors: list[str]) -> None:
        super().__init__("\n".join(errors))
        self.errors = errors


@dataclass(frozen=True)
class RawContent:
    """Everything parsed from the files, drafts included, before references are checked."""

    skills: tuple[Skill, ...] = ()
    roles: tuple[RoleTarget, ...] = ()
    lessons: tuple[Lesson, ...] = ()
    rules: tuple[Rule, ...] = ()
    templates: tuple[DocumentTemplate, ...] = ()
    glossary: tuple[GlossaryTerm, ...] = ()
    exams: tuple[Exam, ...] = ()
    feedback: FeedbackTexts | None = None
    files: tuple[Path, ...] = ()


@dataclass(frozen=True)
class ContentLibrary:
    """Resolved content for one language."""

    skills: Mapping[str, Skill]
    roles: tuple[RoleTarget, ...]
    lessons: Mapping[str, Lesson]
    rules: Mapping[str, Rule]
    templates: Mapping[str, DocumentTemplate]
    glossary: tuple[GlossaryTerm, ...]
    exams: Mapping[str, Exam]
    feedback: FeedbackTexts | None = None
    exercises: Mapping[str, Exercise] = field(default_factory=dict)

    def practice_exercises(self, skill: str, niva: str | None = None) -> tuple[Exercise, ...]:
        """Övningar (not kontroll items) for a skill, optionally of one difficulty."""
        return tuple(
            e for lesson in self.lessons.values() for e in lesson.ovningar
            if e.kompetens == skill and (niva is None or e.niva == niva)
        )


def localised(root: Path, relative: Path, lang: str) -> Path:
    """The English file when it exists and English is chosen, else the Swedish one."""
    if lang == "en":
        english = root / ENGLISH_DIR / relative
        if english.exists():
            return english
    return root / relative


def _read_yaml(path: Path, errors: list[str]) -> Any:
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, yaml.YAMLError) as error:
        errors.append(f"{path}: cannot be read: {error}")
        return None


def _parse[M: BaseModel](model: type[M], path: Path, errors: list[str]) -> M | None:
    data = _read_yaml(path, errors)
    if data is None:
        return None
    try:
        return model.model_validate(data)
    except ValidationError as error:
        for issue in error.errors():
            where = ".".join(str(part) for part in issue["loc"]) or "(root)"
            errors.append(f"{path}: {where}: {issue['msg']}")
        return None


def _files(root: Path, folder: str, lang: str) -> list[Path]:
    base = root / folder
    if not base.is_dir():
        return []
    return [localised(root, p.relative_to(root), lang) for p in sorted(base.rglob("*.yaml"))]


def _optional(root: Path, name: str, lang: str) -> Path | None:
    path = localised(root, Path(name), lang)
    return path if path.exists() else None


def read_content(root: Path, lang: str = "sv") -> tuple[RawContent, list[str]]:
    """Parse every content file; returns the parsed content and all schema errors."""
    errors: list[str] = []
    files: list[Path] = []

    def parse_each[M: BaseModel](model: type[M], paths: list[Path]) -> list[M]:
        files.extend(paths)
        return [m for p in paths if (m := _parse(model, p, errors)) is not None]

    catalogue = parse_each(SkillCatalogue, [localised(root, Path(SKILLS_FILE), lang)])
    rule_files = parse_each(RuleFile, _files(root, RULES_DIR, lang))
    lessons = parse_each(Lesson, _files(root, LESSONS_DIR, lang))
    exams = parse_each(Exam, _files(root, EXAMS_DIR, lang))
    templates = parse_each(TemplateFile, [p] if (p := _optional(root, TEMPLATES_FILE, lang))
                           else [])
    glossary = parse_each(Glossary, [p] if (p := _optional(root, GLOSSARY_FILE, lang)) else [])
    feedback = parse_each(FeedbackTexts, [p] if (p := _optional(root, FEEDBACK_FILE, lang))
                          else [])
    raw = RawContent(
        skills=tuple(s for c in catalogue for s in c.kompetenser),
        roles=tuple(r for c in catalogue for r in c.roller),
        lessons=tuple(lessons),
        rules=tuple(r for f in rule_files for r in f.regler),
        templates=tuple(m for f in templates for m in f.mallar),
        glossary=tuple(t for g in glossary for t in g.termer),
        exams=tuple(exams),
        feedback=feedback[0] if feedback else None,
        files=tuple(files),
    )
    return raw, errors


def _index(items: tuple[Any, ...], key: Callable[[Any], str], kind: str,
           errors: list[str]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for item in items:
        identifier = key(item)
        if identifier in result:
            errors.append(f"duplicate {kind} id {identifier}")
        result[identifier] = item
    return result


def _check_lesson(lesson: Lesson, skills: Mapping[str, Skill], rules: Mapping[str, Rule],
                  errors: list[str]) -> None:
    where = f"lesson {lesson.id}"
    for skill in lesson.kompetenser:
        if skill not in skills:
            errors.append(f"{where}: unknown skill {skill}")
    cited = set(lesson.regler) | {e.regel for e in lesson.ovningar + lesson.kontroll}
    for rule_id in sorted(cited):
        rule = rules.get(rule_id)
        if rule is None:
            errors.append(f"{where}: unknown rule {rule_id}")
        elif lesson.status != DRAFT and rule.status == DRAFT:
            errors.append(f"{where}: published lesson cites rule {rule_id} with status utkast")
    for exercise in lesson.ovningar + lesson.kontroll:
        if exercise.kompetens not in skills:
            errors.append(f"exercise {exercise.id}: unknown skill {exercise.kompetens}")


def resolve(raw: RawContent, include_drafts: bool = False) -> tuple[ContentLibrary, list[str]]:
    """Check references between files and build the library; drafts hidden unless asked for."""
    errors: list[str] = []
    skills = _index(raw.skills, lambda s: s.id, "skill", errors)
    all_rules = _index(raw.rules, lambda r: r.id, "rule", errors)
    all_lessons = _index(raw.lessons, lambda lesson: lesson.id, "lesson", errors)
    templates = _index(raw.templates, lambda m: m.id, "template", errors)
    all_exercises = _index(
        tuple(e for lesson in raw.lessons for e in lesson.ovningar + lesson.kontroll),
        lambda e: e.id, "exercise", errors,
    )
    for role in raw.roles:
        for skill in role.kompetenser:
            if skill not in skills:
                errors.append(f"role {role.id}: unknown skill {skill}")
    for lesson in raw.lessons:
        _check_lesson(lesson, skills, all_rules, errors)
    for exam in raw.exams:
        for exercise_id in exam.ovningar:
            if exercise_id not in all_exercises:
                errors.append(f"exam {exam.id}: unknown exercise {exercise_id}")

    def visible(item: Any) -> bool:
        return include_drafts or item.status != DRAFT

    lessons = {k: v for k, v in all_lessons.items() if visible(v)}
    library = ContentLibrary(
        skills=MappingProxyType(skills),
        roles=raw.roles,
        lessons=MappingProxyType(lessons),
        rules=MappingProxyType({k: v for k, v in all_rules.items() if visible(v)}),
        templates=MappingProxyType(templates),
        glossary=raw.glossary,
        exams=MappingProxyType({e.id: e for e in raw.exams if visible(e)}),
        feedback=raw.feedback,
        exercises=MappingProxyType({
            e.id: e for lesson in lessons.values() for e in lesson.ovningar + lesson.kontroll
        }),
    )
    return library, errors


def load_content(root: Path, lang: str = "sv", include_drafts: bool = False) -> ContentLibrary:
    """Load and resolve all content; raises ContentError listing every problem."""
    raw, errors = read_content(root, lang)
    library, reference_errors = resolve(raw, include_drafts)
    errors += reference_errors
    if errors:
        raise ContentError(errors)
    return library
