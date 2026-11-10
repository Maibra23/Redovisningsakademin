"""About the app and privacy: what is stored, the sparkod, the AI tutor, the notice."""

import streamlit as st

from ra.ui.i18n import t
from ra.ui.theme import card, info_box, page_title

ISSUES_URL = "https://github.com/Maibra23/Redovisningsakademin/issues"

SECTIONS: tuple[tuple[str, str], ...] = (
    (
        "Vad appen är",
        "Redovisningsakademin är en gratis övningsapp i extern redovisning. Du lär dig "
        "bokföra med BAS-kontoplanen och får återkoppling på varje svar.",
    ),
    (
        "Vad som sparas",
        "Appen sparar bara din progression: dina svar på övningar, dina verifikationer i "
        "simulatorn och dina provresultat. Du behöver inget konto och ingen inloggning. "
        "Appen sparar inga personuppgifter och använder ingen spårning.",
    ),
    (
        "Din sparkod",
        "Din progression sparas under en slumpmässig sparkod som står i sidans adress. Spara "
        "adressen som bokmärke för att komma tillbaka. Samma länk fungerar på en annan enhet. "
        "Den som får länken kan öppna din progression, så dela den bara med den du vill. "
        "Databasen sparar ett hashvärde av koden och aldrig själva koden.",
    ),
    (
        "AI-handledaren",
        "Frågor som du ställer till AI-handledaren behandlas av Hugging Face. Frågan skickas "
        "med fakta om övningen men utan din sparkod. Skriv inga personuppgifter i dina frågor. "
        "Facit och belopp kommer alltid från appens egen beräkningsmotor.",
    ),
)


def render() -> None:
    page_title(t("Om appen"), t("Om appen och integritet"))
    for title, body in SECTIONS:
        card(t(title), t(body))
    info_box(
        t(
            "Materialet är avsett för utbildning och är inte professionell rådgivning. "
            "Kontrollera alltid aktuella regler innan du tillämpar dem i ett företag."
        )
    )
    st.link_button(t("Rapportera fel"), ISSUES_URL)
