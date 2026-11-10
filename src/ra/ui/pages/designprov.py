"""Sample page that shows the design system in both languages."""

from ra.services.formatting import format_ore
from ra.ui.i18n import t
from ra.ui.theme import card, info_box, kpi_tile, page_title

SAMPLE_AMOUNT_ORE = 1_250_000


def render() -> None:
    """Header, a card, an amount tile and an info box."""
    page_title(
        t("Designprov"),
        "Redovisningsakademin",
        t("Lär dig extern redovisning med BAS-kontoplanen."),
    )
    card(
        t("Belopp i svenskt format"),
        t(
            "Appen räknar alla belopp i hela ören. Beloppen visas med mellanslag som "
            "tusentalsavgränsare och kommatecken som decimaltecken."
        ),
    )
    kpi_tile(t("Exempelbelopp"), format_ore(SAMPLE_AMOUNT_ORE), amount=True)
    info_box(
        t(
            "Kontonamn och svenska redovisningstermer visas på svenska även när du väljer "
            "engelska. Belopp har alltid svenskt format."
        )
    )
