"""Schemas for authored content (content/*.yaml), validated with Pydantic.

Field names follow the Swedish content files (ASCII spelling): a lesson has
the four mandatory fields vad, varfor, hur and nar. Every model is frozen and
rejects unknown fields, so a misspelt key in a content file is an error.
"""

import datetime as dt
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

Status = Literal["utkast", "publicerad"]
ExerciseType = Literal[
    "kontering", "berakning", "klassificering", "hitta_felet", "avstamning", "resonemang"
]
Difficulty = Literal["grund", "medel", "avancerad"]
NormType = Literal["lag", "förordning", "allmänt råd", "vägledning", "myndighetsinformation"]
DocumentKind = Literal[
    "kundfaktura", "kreditfaktura", "leverantorsfaktura", "kvitto", "kontoutdrag",
    "lonespecifikation", "hyresavi", "internt_underlag",
]

NonEmpty = Annotated[str, Field(min_length=1)]
MIN_EXERCISES_PER_LESSON = 3


class _Content(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class RangeSpec(_Content):
    """A sampled integer parameter: min, max and step (öre for amounts)."""

    min: int
    max: int
    steg: int = Field(default=1, gt=0)

    @model_validator(mode="after")
    def _ordered(self) -> "RangeSpec":
        if self.min > self.max:
            raise ValueError("min must not exceed max")
        return self


ParamSpec = RangeSpec | tuple[str | int, ...]


class Skill(_Content):
    """Kompetens, for example B2 Leverantörsfakturor."""

    id: NonEmpty
    namn: NonEmpty
    modul: NonEmpty


class RoleTarget(_Content):
    """Rollmål: the skills a role needs at Kompetent."""

    id: NonEmpty
    namn: NonEmpty
    kompetenser: tuple[NonEmpty, ...] = Field(min_length=1)


class SkillCatalogue(_Content):
    kompetenser: tuple[Skill, ...] = Field(min_length=1)
    roller: tuple[RoleTarget, ...] = ()


class ClassificationItem(_Content):
    """One item to place in a category in a klassificering exercise."""

    text: NonEmpty
    kategori: NonEmpty
    konto: int | None = None


class Exercise(_Content):
    """One exercise. Figures come from the recipe; content never holds a key amount.

    kontering, berakning, hitta_felet and avstamning name a recipe.
    berakning names the recipe figure to compute in ``svar``.
    klassificering lists ``poster`` and ``kategorier``.
    resonemang lists ``alternativ`` and the index of the right one in ``ratt``.
    """

    id: NonEmpty
    typ: ExerciseType
    kompetens: NonEmpty
    niva: Difficulty
    regel: NonEmpty
    tips: NonEmpty
    uppgift: str | None = None
    recept: str | None = None
    dokument: str | None = None
    parametrar: dict[str, ParamSpec] = Field(default_factory=dict)
    svar: str | None = None
    fraga: str | None = None
    kategorier: tuple[NonEmpty, ...] = ()
    poster: tuple[ClassificationItem, ...] = ()
    alternativ: tuple[NonEmpty, ...] = ()
    ratt: int | None = None

    @model_validator(mode="after")
    def _fields_for_type(self) -> "Exercise":
        needs_recipe = self.typ in ("kontering", "berakning", "hitta_felet", "avstamning")
        if needs_recipe and not self.recept:
            raise ValueError(f"{self.typ} needs a recept")
        if self.typ == "berakning" and not self.svar:
            raise ValueError("berakning needs svar (the recipe figure to compute)")
        if self.typ == "klassificering":
            if not self.poster or not self.kategorier:
                raise ValueError("klassificering needs poster and kategorier")
            unknown = {p.kategori for p in self.poster} - set(self.kategorier)
            if unknown:
                raise ValueError(f"poster use unknown kategorier: {sorted(unknown)}")
        if self.typ == "resonemang":
            if not self.fraga or len(self.alternativ) < 2 or self.ratt is None:
                raise ValueError("resonemang needs fraga, at least two alternativ and ratt")
            if not 0 <= self.ratt < len(self.alternativ):
                raise ValueError("ratt must point at one of the alternativ")
        return self


class WorkedExample(_Content):
    """Visa: a worked example computed by a recipe with fixed parameters."""

    text: NonEmpty
    recept: NonEmpty
    datum: dt.date
    parametrar: dict[str, str | int] = Field(default_factory=dict)


class Lesson(_Content):
    """Lektion with the four mandatory fields, an example, exercises and a check."""

    id: NonEmpty
    modul: NonEmpty
    titel: NonEmpty
    status: Status
    kompetenser: tuple[NonEmpty, ...] = Field(min_length=1)
    vad: NonEmpty
    varfor: NonEmpty
    hur: NonEmpty
    nar: NonEmpty
    regler: tuple[NonEmpty, ...] = Field(min_length=1)
    exempel: WorkedExample
    ovningar: tuple[Exercise, ...] = Field(min_length=MIN_EXERCISES_PER_LESSON)
    kontroll: tuple[Exercise, ...] = Field(min_length=1)


class Rule(_Content):
    """Regel in the Regelbibliotek: a law, norm or guidance with its official source."""

    id: NonEmpty
    namn: NonEmpty
    lagrum: NonEmpty
    normtyp: NormType
    titel: NonEmpty
    forklaring: NonEmpty
    exempel: NonEmpty
    i_praktiken: NonEmpty
    kalla: NonEmpty
    kontrollerad: dt.date
    status: Status


class RuleFile(_Content):
    regler: tuple[Rule, ...] = Field(min_length=1)


class TemplateRow(_Content):
    """A document row: text (may hold {placeholders} from recipe figures) and a figure key."""

    text: NonEmpty
    belopp: NonEmpty


class DocumentTemplate(_Content):
    """Underlag for a recipe: how its figures are shown as a document."""

    id: NonEmpty
    dokument: DocumentKind
    titel: NonEmpty
    motpart: NonEmpty
    text: str = ""
    rader: tuple[TemplateRow, ...] = Field(min_length=1)
    summor: tuple[TemplateRow, ...] = ()


class TemplateFile(_Content):
    mallar: tuple[DocumentTemplate, ...] = Field(min_length=1)


class GlossaryTerm(_Content):
    """Term in ordlista.yaml with a one sentence definition and the English term."""

    term: NonEmpty
    definition: NonEmpty
    engelska: NonEmpty


class Glossary(_Content):
    termer: tuple[GlossaryTerm, ...] = Field(min_length=1)


class Exam(_Content):
    """Prov: a pool of exercise ids drawn by seed, graded at submission."""

    id: NonEmpty
    titel: NonEmpty
    modul: str | None = None
    antal: int = Field(gt=0)
    godkant_procent: int = Field(ge=0, le=100)
    ovningar: tuple[NonEmpty, ...] = Field(min_length=1)
    status: Status

    @model_validator(mode="after")
    def _pool_large_enough(self) -> "Exam":
        if len(self.ovningar) < self.antal:
            raise ValueError("the pool must hold at least antal exercises")
        return self


class FeedbackCode(_Content):
    """Texts for one error code: a short heading, what was wrong and why."""

    rubrik: NonEmpty
    vad: NonEmpty
    varfor: NonEmpty


class FeedbackPhrases(_Content):
    """Fixed phrases of the feedback panel; {name} marks a value filled in by the app."""

    ratt: NonEmpty
    ratt_kontering: NonEmpty
    ratt_belopp: NonEmpty
    ratt_val: NonEmpty
    ratt_klassificering: NonEmpty
    alternativt_konto: NonEmpty
    fler_fel: NonEmpty


class FeedbackTexts(_Content):
    """content/feedback.yaml: texts per error code, a general text and fixed phrases."""

    koder: dict[str, FeedbackCode]
    allmant: FeedbackCode
    texter: FeedbackPhrases
