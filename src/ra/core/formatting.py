"""Swedish display format for amounts (belopp).

Pure functions, no project or Streamlit imports. Amounts are integer öre;
the output follows Swedish convention: space as thousands separator, comma
as decimal sign and "kr" after the amount. The spaces are non-breaking so
an amount never wraps across two lines.
"""

NBSP = " "
ORE_PER_KRONA = 100


def format_ore(ore: int) -> str:
    """Format an amount in öre as kronor with two decimals.

    Belopp i öre visas i kronor: 1250000 -> "12 500,00 kr".
    Floats are rejected because money is never a float in this app.
    """
    if isinstance(ore, bool) or not isinstance(ore, int):
        raise TypeError(f"Amount must be integer öre, got {type(ore).__name__}")
    sign = "-" if ore < 0 else ""
    kronor, rest = divmod(abs(ore), ORE_PER_KRONA)
    grouped = f"{kronor:,}".replace(",", NBSP)
    return f"{sign}{grouped},{rest:02d}{NBSP}kr"
