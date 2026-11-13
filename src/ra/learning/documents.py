"""Underlag: a recipe's figures laid out by its template from dokumentmallar.yaml.

The document holds amounts as Money and plain text only; the interface
escapes and formats it. A figure the learner must compute is hidden.
"""

import datetime as dt
from collections.abc import Mapping, Set
from dataclasses import dataclass

from ra.core.formatting import format_ore
from ra.core.money import Money
from ra.learning.schemas import DocumentTemplate, TemplateRow


@dataclass(frozen=True)
class DocumentRow:
    """One row; ``amount`` is None when the learner is to compute it."""

    text: str
    amount: Money | None


@dataclass(frozen=True)
class Document:
    kind: str
    title: str
    counterparty: str
    date: dt.date
    text: str
    rows: tuple[DocumentRow, ...]
    totals: tuple[DocumentRow, ...]


def _fill(text: str, figures: Mapping[str, object]) -> str:
    values = {k: format_ore(v.ore) if isinstance(v, Money) else str(v) for k, v in figures.items()}
    return text.format(**values)


def _row(row: TemplateRow, figures: Mapping[str, object], hidden: Set[str]) -> DocumentRow:
    value = figures.get(row.belopp)
    amount = value if isinstance(value, Money) and row.belopp not in hidden else None
    return DocumentRow(_fill(row.text, figures), amount)


def render(template: DocumentTemplate, figures: Mapping[str, object], on_date: dt.date,
           hidden: Set[str] = frozenset()) -> Document:
    """The underlag for one exercise instance; figures named in ``hidden`` show no amount."""
    return Document(
        kind=template.dokument,
        title=template.titel,
        counterparty=template.motpart,
        date=on_date,
        text=_fill(template.text, figures),
        rows=tuple(_row(r, figures, hidden) for r in template.rader),
        totals=tuple(_row(r, figures, hidden) for r in template.summor),
    )
