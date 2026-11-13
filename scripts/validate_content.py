"""Validate everything under content/ and exit with status 1 on any problem.

Checks: schema errors, unknown skill, rule, recipe, template or account, a
lesson missing one of the four fields, fewer than three exercises, every
recipe executed on sampled parameters with its key validated against the
kontoplan, and the Swedish spelling guard from CLAUDE.md section 8.

Usage: python scripts/validate_content.py [--root PATH]
"""

import argparse
import re
import string
import sys
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import yaml

from ra.core.money import Money
from ra.core.voucher import validate
from ra.learning import recipes
from ra.learning.grading import ErrorCode
from ra.learning.loader import ENGLISH_DIR, ContentLibrary, read_content, resolve
from ra.learning.schemas import Exercise, Lesson

DEFAULT_ROOT = Path(__file__).resolve().parents[1] / "content"
SAMPLED_SEEDS = range(5)

# Common ASCII misspellings of Swedish words (å, ä, ö written as a or o, or as aa, ae, oe).
MISSPELLINGS = re.compile(
    r"\b(bokfor\w*|forsalj\w*|leverantor\w*|inkop\w*|utgaende|ingaende|tillgang\w*|"
    r"\w*rakning\w*|rabalans\w*|forutbetal\w*|avstamn\w*|foretag\w*|arsredovis\w*|"
    r"mervardes\w*|lon|loner|lonen|lonespec\w*|ranta|rantor|rantan|overfor\w*|"
    r"bokfoer\w*|foeretag\w*|foersaelj\w*|maanad\w*|loen\w*|raekning\w*)\b",
    re.IGNORECASE,
)
# The owner wants no dash characters as punctuation in running text.
DASH_PUNCTUATION = re.compile(r"[–—]| - ")
# Keys whose values are identifiers, codes or addresses, not learner facing text.
IDENTIFIER_KEYS = frozenset({
    "id", "recept", "dokument", "regel", "regler", "kompetens", "kompetenser", "typ",
    "niva", "status", "kalla", "svar", "belopp", "modul", "parametrar", "kategori",
    "kind", "normal_side", "report_line", "moms_role", "code", "url", "source", "key",
    "unit", "ovningar",
})


def _text_values(node: Any, path: str = "") -> Iterator[tuple[str, str]]:
    if isinstance(node, dict):
        for key, value in node.items():
            if key not in IDENTIFIER_KEYS:
                yield from _text_values(value, f"{path}.{key}" if path else str(key))
    elif isinstance(node, list):
        for index, value in enumerate(node):
            yield from _text_values(value, f"{path}[{index}]")
    elif isinstance(node, str):
        yield path, node


def check_spelling(root: Path) -> list[str]:
    """Swedish files only; English files under content/en are skipped."""
    errors: list[str] = []
    for path in sorted(root.rglob("*.yaml")):
        if ENGLISH_DIR in path.relative_to(root).parts[:1]:
            continue
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        for where, text in _text_values(data):
            for match in MISSPELLINGS.finditer(text):
                errors.append(f"{path}: {where}: '{match.group(0)}' is missing å, ä or ö")
            if DASH_PUNCTUATION.search(text):
                errors.append(f"{path}: {where}: dash used as punctuation; rewrite the sentence")
    return errors


def _placeholders(text: str) -> set[str]:
    return {name for _, name, _, _ in string.Formatter().parse(text) if name}


def _check_template(library: ContentLibrary, template_id: str, figures: dict[str, Any],
                    where: str) -> list[str]:
    template = library.templates.get(template_id)
    if template is None:
        return [f"{where}: no document template {template_id} in dokumentmallar.yaml"]
    errors = []
    texts = [template.text]
    for row in template.rader + template.summor:
        texts.append(row.text)
        if not isinstance(figures.get(row.belopp), Money):
            errors.append(f"{where}: template {template_id} shows unknown amount {row.belopp}")
    missing = set().union(*(_placeholders(text) for text in texts)) - set(figures)
    if missing:
        errors.append(f"{where}: template {template_id} uses unknown figures {sorted(missing)}")
    return errors


def _check_recipe_run(ctx: recipes.RecipeContext, library: ContentLibrary, name: str,
                      seed: int, exercise: Exercise | None = None) -> list[str]:
    where = f"exercise {exercise.id} (seed {seed})" if exercise else f"recipe {name} (seed {seed})"
    overrides = exercise.parametrar if exercise else None
    try:
        result = recipes.generate(ctx, name, seed, overrides).result
    except (recipes.RecipeError, ValueError) as error:
        return [f"{where}: recipe failed: {error}"]
    errors = [f"{where}: key {issue.code.value} {issue.account or ''}".rstrip()
              for issue in validate(ctx.chart, result.voucher)]
    for key_account, accepted in result.alternatives.items():
        errors += [f"{where}: unknown alternative account {a} for {key_account}"
                   for a in accepted if a not in ctx.chart]
    svar = exercise.svar if exercise else None
    if svar is not None and not isinstance(result.figures.get(svar), Money):
        errors.append(f"{where}: svar {svar} is not an amount the recipe produces")
    template_id = (exercise.dokument if exercise else None) or name
    return errors + _check_template(library, template_id, dict(result.figures), where)


def check_recipes(ctx: recipes.RecipeContext, library: ContentLibrary) -> list[str]:
    """Every registered recipe on its default ranges: valid key and a working template."""
    return [error for name in recipes.recipe_names() for seed in SAMPLED_SEEDS
            for error in _check_recipe_run(ctx, library, name, seed)]


def check_exercise(ctx: recipes.RecipeContext, library: ContentLibrary,
                   exercise: Exercise) -> list[str]:
    errors = [f"exercise {exercise.id}: unknown account {item.konto}"
              for item in exercise.poster if item.konto is not None and item.konto not in ctx.chart]
    if exercise.recept is None:
        return errors
    if exercise.recept not in recipes.recipe_names():
        return errors + [f"exercise {exercise.id}: unknown recipe {exercise.recept}"]
    for seed in SAMPLED_SEEDS:
        errors += _check_recipe_run(ctx, library, exercise.recept, seed, exercise)
    return errors


def check_example(ctx: recipes.RecipeContext, lesson: Lesson) -> list[str]:
    example = lesson.exempel
    where = f"lesson {lesson.id} exempel"
    if example.recept not in recipes.recipe_names():
        return [f"{where}: unknown recipe {example.recept}"]
    try:
        result = recipes.run(ctx, example.recept, example.datum, example.parametrar)
    except (recipes.RecipeError, ValueError) as error:
        return [f"{where}: recipe failed: {error}"]
    return [f"{where}: key {issue.code.value}" for issue in validate(ctx.chart, result.voucher)]


def check_english_mirror(root: Path) -> list[str]:
    """Every English lesson must keep the ids, recipes and parameters of its Swedish source."""
    if not (root / ENGLISH_DIR).is_dir():
        return []
    swedish = {lesson.id: lesson for lesson in read_content(root, "sv")[0].lessons}
    errors = []
    for lesson in read_content(root, ENGLISH_DIR)[0].lessons:
        source = swedish.get(lesson.id)
        if source is None:
            errors.append(f"content/en: lesson {lesson.id} has no Swedish source")
            continue
        pairs = ((lesson.ovningar, source.ovningar), (lesson.kontroll, source.kontroll))
        for ours, theirs in pairs:
            mine = [(e.id, e.recept, e.typ, e.kompetens, e.niva, e.regel, e.parametrar, e.svar)
                    for e in ours]
            same = [(e.id, e.recept, e.typ, e.kompetens, e.niva, e.regel, e.parametrar, e.svar)
                    for e in theirs]
            if mine != same:
                errors.append(f"content/en: lesson {lesson.id} exercises differ from the Swedish "
                              f"source in id, recipe, type, skill, level, rule, parameters or svar")
        if (lesson.exempel.recept, lesson.exempel.parametrar, lesson.exempel.datum) != (
                source.exempel.recept, source.exempel.parametrar, source.exempel.datum):
            errors.append(f"content/en: lesson {lesson.id} example differs from the Swedish source")
    return errors


def check_feedback(library: ContentLibrary) -> list[str]:
    """feedback.yaml must exist and have texts for exactly the grader's error codes."""
    if library.feedback is None:
        return ["feedback.yaml is missing"]
    codes = {code.value for code in ErrorCode}
    written = set(library.feedback.koder)
    return ([f"feedback.yaml: no texts for {code}" for code in sorted(codes - written)]
            + [f"feedback.yaml: unknown code {code}" for code in sorted(written - codes)])


def validate_content(root: Path) -> tuple[list[str], str]:
    """All problems found under ``root`` and a one line summary."""
    errors: list[str] = []
    raw, schema_errors = read_content(root, "sv")
    errors += schema_errors
    errors += read_content(root, "en")[1] if (root / ENGLISH_DIR).is_dir() else []
    library, reference_errors = resolve(raw, include_drafts=True)
    errors += reference_errors
    ctx = recipes.load_context(root)
    errors += check_recipes(ctx, library)
    errors += check_feedback(library)
    errors += check_english_mirror(root)
    for lesson in library.lessons.values():
        errors += check_example(ctx, lesson)
        for exercise in lesson.ovningar + lesson.kontroll:
            errors += check_exercise(ctx, library, exercise)
    errors += check_spelling(root)
    summary = (f"{len(library.lessons)} lessons, {len(library.exercises)} exercises, "
               f"{len(library.rules)} rules, {len(recipes.recipe_names())} recipes")
    return list(dict.fromkeys(errors)), summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    args = parser.parse_args()
    errors, summary = validate_content(args.root)
    for error in errors:
        print(error)
    print(f"{'FAILED' if errors else 'OK'}: {summary}, {len(errors)} problems")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
