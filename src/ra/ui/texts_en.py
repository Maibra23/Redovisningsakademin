"""English interface texts, keyed by the Swedish source text.

See ra/ui/i18n.py. Numbered placeholders ({0}, {1}, ...) must appear in the
English text too. Account names, document contents and Swedish accounting
terms stay in Swedish, with the English explanation beside them.
"""

EN: dict[str, str] = {
    # Sidebar
    "Språk": "Language",
    # Design sample page
    "Designprov": "Design sample",
    "Lär dig extern redovisning med BAS-kontoplanen.":
        "Learn financial accounting with the Swedish chart of accounts (BAS-kontoplanen).",
    "Belopp i svenskt format": "Amounts in Swedish format",
    "Appen räknar alla belopp i hela ören. Beloppen visas med mellanslag som "
    "tusentalsavgränsare och kommatecken som decimaltecken.":
        "The app calculates every amount in whole öre. Amounts are shown with a space "
        "as thousands separator and a comma as decimal sign.",
    "Exempelbelopp": "Sample amount",
    "Kontonamn och svenska redovisningstermer visas på svenska även när du väljer "
    "engelska. Belopp har alltid svenskt format.":
        "Account names and Swedish accounting terms stay in Swedish even when you choose "
        "English. Amounts always use the Swedish format.",
}
