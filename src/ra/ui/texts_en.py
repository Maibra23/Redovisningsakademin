"""English interface texts, keyed by the Swedish source text.

See ra/ui/i18n.py. Numbered placeholders ({0}, {1}, ...) must appear in the
English text too. Account names, document contents and Swedish accounting
terms stay in Swedish, with the English explanation beside them.
"""

EN: dict[str, str] = {
    # Sidebar
    "Språk": "Language",
    "Rapportera fel": "Report an error",
    # Navigation groups and pages
    "Hem": "Home",
    "Lär": "Learn",
    "Praktik": "Practice",
    "Min utveckling": "My progress",
    "Översikt": "Overview",
    "Lektioner": "Lessons",
    "Övningar": "Exercises",
    "Repetition": "Review",
    "Prov": "Exams",
    "Bokföringssimulatorn": "Bookkeeping simulator",
    "Regelbibliotek": "Rule library",
    "Kontoplan": "Chart of accounts (kontoplan)",
    "Kompetensprofil": "Skills profile",
    "Prestationer": "Achievements",
    "Inställningar": "Settings",
    # Placeholder sentences
    "Lektionerna förklarar varje moment med ett genomräknat exempel.":
        "The lessons explain each topic with a worked example.",
    "Övningarna ger dig nya siffror varje gång och återkoppling på varje svar.":
        "The exercises give you new figures every time and feedback on every answer.",
    "Repetitionen tar tillbaka det du har övat efter en, tre och sju dagar.":
        "Review brings back what you have practised after one, three and seven days.",
    "Proven visar vad du kan utan ledtrådar.":
        "The exams show what you can do without hints.",
    "I simulatorn bokför du en hel månad för ett fiktivt aktiebolag.":
        "In the simulator you keep the books for a whole month of a fictional "
        "limited company (aktiebolag).",
    "Regelbiblioteket samlar reglerna som övningarna hänvisar till, med källa.":
        "The rule library collects the rules the exercises refer to, with their sources.",
    "Kontoplanen visar de konton i BAS-kontoplanen som appen använder.":
        "The chart of accounts shows the accounts from BAS-kontoplanen that the app uses.",
    "Kompetensprofilen visar hur säker du är på varje färdighet.":
        "The skills profile shows how confident you are in each skill.",
    "Här ser du dina prestationer och din XP.":
        "Here you see your achievements and your XP.",
    "Här hittar du din sparkod och kan återställa eller radera din progression.":
        "Here you find your save code (sparkod) and can reset or delete your progress.",
    # Start view
    "Välkommen till Redovisningsakademin": "Welcome to Redovisningsakademin",
    "Öva svensk bokföring med BAS-kontoplanen och få veta exakt vad som blev fel "
    "och varför.":
        "Practise Swedish bookkeeping with the BAS chart of accounts (BAS-kontoplanen) "
        "and learn exactly what went wrong and why.",
    "Jag är ny": "I am new",
    "Börja med grunderna. Lektionerna förklarar varje moment med ett exempel.":
        "Start with the basics. The lessons explain each topic with an example.",
    "Till lektionerna": "Go to the lessons",
    "Jag har erfarenhet": "I have experience",
    "Gå direkt till övningarna och träna det du behöver.":
        "Go straight to the exercises and practise what you need.",
    "Till övningarna": "Go to the exercises",
    # About and privacy
    "Om appen": "About",
    "Om appen och integritet": "About and privacy",
    "Vad appen är": "What the app is",
    "Redovisningsakademin är en gratis övningsapp i extern redovisning. Du lär dig "
    "bokföra med BAS-kontoplanen och får återkoppling på varje svar.":
        "Redovisningsakademin is a free practice app for financial accounting (extern "
        "redovisning). You learn bookkeeping with the BAS chart of accounts and get "
        "feedback on every answer.",
    "Vad som sparas": "What is stored",
    "Appen sparar bara din progression: dina svar på övningar, dina verifikationer i "
    "simulatorn och dina provresultat. Du behöver inget konto och ingen inloggning. "
    "Appen sparar inga personuppgifter och använder ingen spårning.":
        "The app stores only your progress: your answers to exercises, your vouchers "
        "(verifikationer) in the simulator and your exam results. You need no account "
        "and no login. The app stores no personal data and uses no tracking.",
    "Din sparkod": "Your save code (sparkod)",
    "Din progression sparas under en slumpmässig sparkod som står i sidans adress. Spara "
    "adressen som bokmärke för att komma tillbaka. Samma länk fungerar på en annan enhet. "
    "Den som får länken kan öppna din progression, så dela den bara med den du vill. "
    "Databasen sparar ett hashvärde av koden och aldrig själva koden.":
        "Your progress is saved under a random save code that appears in the page "
        "address. Bookmark the address to come back. The same link works on another "
        "device. Anyone who gets the link can open your progress, so share it only with "
        "people you choose. The database stores a hash of the code and never the code "
        "itself.",
    "AI-handledaren": "The AI tutor",
    "Frågor som du ställer till AI-handledaren behandlas av Hugging Face. Frågan skickas "
    "med fakta om övningen men utan din sparkod. Skriv inga personuppgifter i dina frågor. "
    "Facit och belopp kommer alltid från appens egen beräkningsmotor.":
        "Questions you ask the AI tutor are processed by Hugging Face. The question is "
        "sent with facts about the exercise but without your save code. Do not write "
        "personal data in your questions. Answer keys and amounts always come from the "
        "app's own calculation engine.",
    "Materialet är avsett för utbildning och är inte professionell rådgivning. "
    "Kontrollera alltid aktuella regler innan du tillämpar dem i ett företag.":
        "The material is for education and is not professional advice. Always check "
        "the current rules before you apply them in a business.",
    # Övningar page
    "Öva med nya siffror varje gång. Du får återkoppling på varje svar.":
        "Practise with new figures every time. You get feedback on every answer.",
    "Det finns inga publicerade övningar ännu.": "There are no published exercises yet.",
    "Det finns ingen övning på den här nivån ännu.":
        "There is no exercise at this level yet.",
    "Område": "Topic",
    "Nivå": "Level",
    "Grund": "Basic",
    "Medel": "Intermediate",
    "Avancerad": "Advanced",
    "Din nivå": "Your level",
    "Ej påbörjad": "Not started (ej påbörjad)",
    "Övar": "Practising (övar)",
    "Kompetent": "Competent (kompetent)",
    "Befäst": "Consolidated (befäst)",
    "Rätt bland de senaste": "Correct among the latest",
    "{0} % av {1} försök": "{0} % of {1} attempts",
    "Inga försök ännu": "No attempts yet",
    "Nästa repetition": "Next review",
    "Inte planerad": "Not scheduled",
    "Bokför underlaget.": "Book the source document (underlag).",
    "Beräkna beloppet som saknas.": "Calculate the missing amount.",
    "Placera varje post i rätt grupp.": "Place each item in the right group.",
    "Välj det bästa svaret.": "Choose the best answer.",
    "Verifikationen nedan innehåller ett fel. Bokför en rättelseverifikation.":
        "The voucher (verifikation) below contains an error. Book a correcting voucher "
        "(rättelseverifikation).",
    "Jämför kontoutdraget med bankkontot i huvudboken. Markera raderna som skiljer sig och "
    "bokför det som behövs för att saldona ska stämma.":
        "Compare the bank statement (kontoutdrag) with the bank account in the general ledger "
        "(huvudbok). Mark the lines that differ and book what is needed for the balances to "
        "agree.",
    "Ditt svar i kronor": "Your answer in kronor",
    "Till exempel 1 250,50": "For example 1 250,50",
    "Välj grupp": "Choose a group",
    "Alternativ": "Options",
    "Bokförd verifikation": "Booked voucher (verifikation)",
    "Din rättelseverifikation": "Your correcting voucher (rättelseverifikation)",
    "Kontoutdrag": "Bank statement (kontoutdrag)",
    "Bankkontot i huvudboken": "The bank account in the general ledger (huvudbok)",
    "Dina verifikationer": "Your vouchers (verifikationer)",
    "Rätta svaret": "Check the answer",
    "Ny uppgift": "New exercise",
    "Visa tips": "Show hint",
    "Ett belopp kunde inte läsas. Skriv beloppet med siffror, till exempel 1 250,50.":
        "An amount could not be read. Write the amount in figures, for example 1 250,50.",
    "En rad har ett belopp men inget konto. Välj ett konto för varje rad med belopp.":
        "A row has an amount but no account. Choose an account for every row with an amount.",
    "En rad har belopp i både debet och kredit. Skriv varje belopp på en egen rad.":
        "A row has amounts in both debet and kredit. Write each amount on its own row.",
    "Du har inte skrivit något svar ännu.": "You have not written an answer yet.",
    "Försök {0} på samma uppgift ger ingen XP och räknas inte för din nivå.":
        "Attempt {0} on the same exercise gives no XP and does not count towards your level.",
    "Du fick {0} XP. Totalt har du {1} XP.": "You earned {0} XP. Your total is {1} XP.",
    "Du fick {0} XP. Totalt har du {1} XP. Fler rätt på samma övning i dag ger mindre eller "
    "ingen XP.":
        "You earned {0} XP. Your total is {1} XP. More correct answers on the same exercise "
        "today give less or no XP.",
    # Verifikation component
    "Konto": "Account (konto)",
    "Kontonamn": "Account name (kontonamn)",
    "Konto och kontonamn": "Account and account name",
    "Debet": "Debet (debit)",
    "Kredit": "Kredit (credit)",
    "Summa": "Total (summa)",
    "Skriv kontonummer eller kontonamn för att söka.":
        "Type an account number or account name to search.",
    "Belopp i kronor, till exempel 1 250,50.": "Amount in kronor, for example 1 250,50.",
    "Skriv in verifikationens rader. Summorna visas här.":
        "Enter the rows of the voucher. The totals appear here.",
    "✓ Verifikationen balanserar. Summa debet {0}, summa kredit {1}.":
        "✓ The voucher balances. Total debet {0}, total kredit {1}.",
    "✗ Verifikationen balanserar inte. Summa debet {0}, summa kredit {1}, differens {2}.":
        "✗ The voucher does not balance. Total debet {0}, total kredit {1}, difference {2}.",
    # Document viewer and statement
    "Underlag": "Source document (underlag)",
    "Att beräkna": "To calculate",
    "Datum": "Date",
    "Text": "Text",
    "Belopp": "Amount",
    "Skiljer sig": "Differs",
    # Feedback panel
    "Vad som blev fel": "What went wrong",
    "Varför": "Why",
    "Rätt hantering": "Correct treatment",
    "Regel": "Rule",
    "Tips": "Tip",
    "Läs regeln hos källan": "Read the rule at the source",
}
