"""The Inkorg: the documents visible up to the current day, built from the month.

A document is laid out by its template (the scenario's own for the month
recipes, else the recipe's template in content/dokumentmallar.yaml) with the
figures of the event's recipe for the run's seed, so amounts differ per run.
The counterparty and the text come from the scenario. The current day is the
date of the earliest document not yet booked, so the learner works through
the month in order: every document dated on or before that day is visible.
"""

import datetime as dt
from collections.abc import Mapping, Set
from dataclasses import replace

from ra.core.formatting import format_date, format_ore
from ra.core.money import Money
from ra.learning import documents
from ra.learning.documents import Document
from ra.learning.schemas import DocumentTemplate
from ra.simulator.scenario import Event, Month, RealisedEvent, Scenario


class DocumentError(LookupError):
    """No template for an event, or its text names a field that does not exist."""


def current_day(scenario: Scenario, booked: Set[str]) -> dt.date:
    """The date of the earliest event without a verifikation; the month's end when none."""
    pending = [e.datum for e in scenario.events if e.id not in booked]
    return min(pending, default=scenario.month_end)


def visible(scenario: Scenario, booked: Set[str]) -> tuple[Event, ...]:
    """Events whose document has arrived: dated on or before the current day."""
    day = current_day(scenario, booked)
    return tuple(e for e in scenario.events if e.datum <= day)


def template_for(scenario: Scenario, templates: Mapping[str, DocumentTemplate],
                 event: Event) -> DocumentTemplate:
    template = scenario.templates.get(event.recept) or templates.get(event.recept)
    if template is None:
        raise DocumentError(f"event {event.id}: no document template for {event.recept}")
    return template


def _invoice_reference(scenario: Scenario, avser: str | None) -> str:
    """The invoice number an event refers to: an earlier event's number, or the number itself."""
    if avser is None:
        return ""
    earlier = scenario.event(avser)
    return earlier.fakturanummer or "" if earlier is not None else avser


def fields(scenario: Scenario, realised: RealisedEvent) -> dict[str, str]:
    """Text values a document can name: event, counterparty, company and recipe figures."""
    event, company = realised.event, scenario.company
    party = scenario.party(event.motpart) if event.motpart else None
    values = {k: format_ore(v.ore) if isinstance(v, Money) else str(v)
              for k, v in realised.result.figures.items()}
    values |= {
        "bolag": company.namn, "bolag_orgnr": company.orgnr,
        "bolag_momsnr": company.momsnr, "datum": format_date(event.datum),
        "fakturanummer": event.fakturanummer or "",
        "avser": _invoice_reference(scenario, event.avser),
    }
    if party is not None:
        due = event.datum + dt.timedelta(days=party.betalningsvillkor_dagar)
        values |= {"motpart": party.namn, "motpart_orgnr": party.orgnr or "",
                   "motpart_momsnr": party.momsnr or "",
                   "villkor": str(party.betalningsvillkor_dagar), "forfallodag": format_date(due)}
    return values


def render(scenario: Scenario, templates: Mapping[str, DocumentTemplate],
           realised: RealisedEvent) -> Document:
    """The document for one event in this run."""
    event = realised.event
    figures: dict[str, object] = dict(realised.result.figures)
    if event.beskrivning:
        figures["beskrivning"] = event.beskrivning
    layout = documents.render(template_for(scenario, templates, event), figures, event.datum,
                              frozenset(event.dolda))
    party = scenario.party(event.motpart) if event.motpart else None
    try:
        text = event.text.format(**fields(scenario, realised))
    except (KeyError, IndexError, ValueError) as error:
        raise DocumentError(f"event {event.id}: text names an unknown field {error}") from error
    return replace(layout, counterparty=party.namn if party else layout.counterparty, text=text)


def check(scenario: Scenario, templates: Mapping[str, DocumentTemplate],
          month: Month) -> list[str]:
    """Every event's document can be rendered and hides only figures its recipe produces."""
    errors: list[str] = []
    for realised in month.events:
        event = realised.event
        where = f"event {event.id} (seed {month.seed})"
        unknown = set(event.dolda) - set(realised.result.figures)
        if unknown:
            errors.append(f"{where}: dolda names unknown figures {sorted(unknown)}")
        try:
            template = template_for(scenario, templates, event)
            render(scenario, templates, realised)
        except DocumentError as error:
            errors.append(f"{where}: {error}")
            continue
        except KeyError as error:
            errors.append(f"{where}: template {template.id} uses unknown figure {error}")
            continue
        errors += [f"{where}: template {template.id} shows unknown amount {row.belopp}"
                   for row in template.rader + template.summor
                   if not isinstance(realised.result.figures.get(row.belopp), Money)]
    return errors
