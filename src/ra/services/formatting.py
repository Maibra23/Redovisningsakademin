"""Display formatting for the interface layer, which imports services only."""

import datetime as dt

from ra.core.formatting import format_ore

MONTHS = ("januari", "februari", "mars", "april", "maj", "juni", "juli", "augusti",
          "september", "oktober", "november", "december")


def format_date(day: dt.date) -> str:
    """Swedish date as in running text: 15 januari 2026."""
    return f"{day.day} {MONTHS[day.month - 1]} {day.year}"


__all__ = ["format_date", "format_ore"]
