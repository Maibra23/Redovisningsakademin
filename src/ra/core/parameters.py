"""Dated parameters such as the arbetsgivaravgift rate (``content/parametrar.yaml``).

A value is looked up by key and the date of the transaction, so a change in
the law is a new row with a new valid_from, never a change in code.
"""

import datetime as dt
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path
from typing import Any

import yaml


class ParameterError(ValueError):
    """A parameter is missing, overlapping or not valid."""


@dataclass(frozen=True)
class Parameter:
    key: str
    value: Fraction
    unit: str
    valid_from: dt.date | None
    valid_to: dt.date | None
    source: str
    checked_on: dt.date

    def covers(self, on_date: dt.date) -> bool:
        after_start = self.valid_from is None or on_date >= self.valid_from
        before_end = self.valid_to is None or on_date <= self.valid_to
        return after_start and before_end


class ParameterTable:
    """All dated parameters, looked up by key and date."""

    def __init__(self, parameters: tuple[Parameter, ...]) -> None:
        self._parameters = parameters
        for p in parameters:
            if sum(1 for q in parameters if q.key == p.key and _overlaps(p, q)) > 1:
                raise ParameterError(f"Overlapping values for {p.key}")

    def value_for(self, key: str, on_date: dt.date) -> Fraction:
        matches = [p for p in self._parameters if p.key == key and p.covers(on_date)]
        if not matches:
            raise ParameterError(f"No value for {key} on {on_date.isoformat()}")
        return matches[0].value


def _overlaps(a: Parameter, b: Parameter) -> bool:
    a_start, a_end = a.valid_from or dt.date.min, a.valid_to or dt.date.max
    b_start, b_end = b.valid_from or dt.date.min, b.valid_to or dt.date.max
    return a_start <= b_end and b_start <= a_end


def _parse(raw: dict[str, Any]) -> Parameter:
    try:
        return Parameter(
            key=str(raw["key"]),
            value=Fraction(str(raw["value"])),
            unit=str(raw["unit"]),
            valid_from=raw.get("valid_from"),
            valid_to=raw.get("valid_to"),
            source=str(raw["source"]),
            checked_on=raw["checked_on"],
        )
    except (KeyError, ValueError, TypeError) as error:
        raise ParameterError(f"Invalid parameter entry {raw!r}: {error}") from error


def load_parameters(path: Path) -> ParameterTable:
    """Load ``content/parametrar.yaml``."""
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not isinstance(data.get("parameters"), list):
        raise ParameterError(f"{path}: expected a mapping with a 'parameters' list")
    return ParameterTable(tuple(_parse(raw) for raw in data["parameters"]))
