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
    "Rätta igen (räknas inte)": "Check again (does not count)",
    "Markera en cell och tryck Enter för att skriva. Skriv kontonumret för att hitta kontot. "
    "Lägg till rader med plustecknet.":
        "Select a cell and press Enter to type. Type the account number to find the account. "
        "Add rows with the plus sign.",
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
    # Lessons
    "Varje lektion förklarar, visar ett exempel, låter dig öva och avslutas med en kontroll.":
        "Each lesson explains, shows a worked example, lets you practise and ends with a check.",
    "Det finns inga publicerade lektioner ännu.": "There are no published lessons yet.",
    "{0} av {1} lektioner klara": "{0} of {1} lessons done",
    "✓ Klar": "✓ Done",
    "Inte klar": "Not done",
    "Öppna": "Open",
    "Till alla lektioner": "All lessons",
    "Du har klarat kontrollen i den här lektionen.": "You have passed the check in this lesson.",
    "1 Förklara": "1 Explain",
    "2 Visa": "2 Show",
    "3 Gör": "3 Do",
    "4 Kontroll": "4 Check",
    "Vad": "What (vad)",
    "Hur": "How (hur)",
    "När": "When (när)",
    "Regler": "Rules",
    "Förenklat exempel: {0}": "Simplified example: {0}",
    "Verifikation": "Voucher (verifikation)",
    "Effekt på rapporterna": "Effect on the reports",
    "Resultaträkning": "Income statement (resultaträkning)",
    "Tillgångar": "Assets (tillgångar)",
    "Eget kapital och skulder": "Equity and liabilities (eget kapital och skulder)",
    "Summa tillgångar": "Total assets",
    "Summa eget kapital och skulder": "Total equity and liabilities",
    "Förändring": "Change",
    "Ingen förändring": "No change",
    "Övning": "Exercise",
    "Övning {0}": "Exercise {0}",
    "Kontrollen har inga tips. Lektionen är klar när du har svarat rätt på varje fråga i "
    "kontrollen.":
        "The check has no tips. The lesson is done when you have answered every question in "
        "the check correctly.",
    "Fråga {0}": "Question {0}",
    "Rätt på kontrollen.": "Correct on the check.",
    "Materialet är till för utbildning och är inte juridisk eller skattemässig rådgivning.":
        "The material is for education and is not legal or tax advice.",
    # Rule library
    "Reglerna som lektionerna och övningarna hänvisar till, med källa och datum för den "
    "senaste kontrollen.":
        "The rules that the lessons and exercises refer to, with the source and the date of "
        "the latest check.",
    "Materialet är till för utbildning och är inte juridisk eller skattemässig rådgivning. "
    "Läs alltid den aktuella texten hos källan.":
        "The material is for education and is not legal or tax advice. Always read the "
        "current text at the source.",
    "Sök": "Search",
    "Till exempel verifikation eller moms": "For example verifikation or moms",
    "Normtyp": "Type of norm",
    "Lag": "Act (lag)",
    "Förordning": "Ordinance (förordning)",
    "Allmänt råd": "General guidance (allmänt råd)",
    "Vägledning": "Guide (vägledning)",
    "Myndighetsinformation": "Agency information (myndighetsinformation)",
    "{0} regler": "{0} rules",
    "Ingen regel matchar sökningen.": "No rule matches the search.",
    "Källa": "Source",
    "Lagrum": "Section (lagrum)",
    "Förklaring": "Explanation",
    "Exempel": "Example",
    "I praktiken": "In practice",
    "Senast kontrollerad: {0}": "Last checked: {0}",
    # Chart of accounts
    "Kontona i BAS-kontoplanen som appen använder, ordnade efter kontoklass.":
        "The accounts in the BAS chart of accounts that the app uses, grouped by account "
        "class (kontoklass).",
    "Kontonummer och kontonamn kommer från {0}, utgiven av BAS. Upphovsrätten till "
    "kontoplanen tillhör BAS. Appen visar bara de konton som lektionerna och övningarna "
    "använder. Kontrollerad mot källan {1}.":
        "Account numbers and names come from {0}, published by BAS. The copyright to the chart "
        "of accounts belongs to BAS. The app shows only the accounts that the lessons and "
        "exercises use. Checked against the source on {1}.",
    "BAS-kontoplanen hos BAS": "The BAS chart of accounts at BAS",
    "Sök konto": "Search account",
    "Kontonummer eller kontonamn, till exempel 1930 eller moms":
        "Account number or account name, for example 1930 or moms",
    "Inget konto matchar sökningen.": "No account matches the search.",
    "Kontoklass {0}: {1}": "Account class (kontoklass) {0}: {1}",
    "Kostnader för varor och material": "Costs of goods and materials",
    "Övriga externa kostnader": "Other external costs",
    "Kostnader för personal och avskrivningar": "Personnel costs and depreciation",
    "Finansiella poster och skatt": "Financial items and tax",
    "Rörelsens inkomster": "Operating income",
    "Typ": "Type",
    "Ökar i": "Increases on",
    "Tillgång": "Asset (tillgång)",
    "Eget kapital": "Equity (eget kapital)",
    "Skuld": "Liability (skuld)",
    "Intäkt": "Revenue (intäkt)",
    "Kostnad": "Expense (kostnad)",
    "Typ och sidan där kontot ökar är appens egen indelning och ingår inte i BAS publikation.":
        "The type and the side on which the account increases are the app's own "
        "classification and are not part of the BAS publication.",
    # Review
    "Det du har övat kommer tillbaka efter en, tre och sju dagar, med nya siffror.":
        "What you have practised comes back after one, three and seven days, with new figures.",
    "Du har inget att repetera i dag. När du har övat på en färdighet kommer den tillbaka här "
    "efter en dag.":
        "You have nothing to review today. When you have practised a skill it comes back here "
        "after one day.",
    "I dag är det dags att repetera {0} färdigheter.": "Today {0} skills are due for review.",
    "{0} {1}, planerad {2}": "{0} {1}, due {2}",
    "Starta repetitionen": "Start the review",
    "En repetition tar högst {0} färdigheter åt gången. De övriga finns kvar nästa gång du "
    "öppnar sidan.":
        "A review takes at most {0} skills at a time. The others remain for the next time you "
        "open the page.",
    "Uppgift {0} av {1}": "Task {0} of {1}",
    "Nästa uppgift": "Next task",
    "Visa sammanfattningen": "Show the summary",
    "Sammanfattning": "Summary",
    "Du svarade rätt på {0} av {1} uppgifter.": "You answered {0} of {1} tasks correctly.",
    "✓ Rätt": "✓ Correct",
    "✗ Fel": "✗ Wrong",
    "{0} {1} {2}. Nästa repetition: {3}.": "{0} {1} {2}. Next review: {3}.",
    "Avsluta repetitionen": "End the review",
    # Bokföringssimulatorn (D5.3)
    "Alla dokument för {0} är bokförda. Fortsätt med rapporterna och månadens avslut.":
        "Every document for {0} is booked. Continue with the reports and the month end.",
    "Bokför": "Book (bokför)",
    "Bokför rättelsen": "Book the correction",
    "Bokfört som verifikation {0}.": "Booked as voucher (verifikation) {0}.",
    "Du är redovisningsansvarig på Nordvik Kontorsmiljö AB och bokför en hel månad.":
        "You are the accountant of Nordvik Kontorsmiljö AB and keep the books for a whole month.",
    "En bokförd verifikation får inte ändras. Du rättar den med en ny verifikation som hänvisar "
    "till den gamla, till exempel genom att vända den felaktiga och bokföra rätt, eller genom att "
    "bokföra bara skillnaden.":
        "A booked voucher (verifikation) must not be changed. You correct it with a new voucher "
        "that refers to the old one, for example by reversing the wrong one and booking it "
        "correctly, or by booking only the difference.",
    "Företaget, personerna och alla nummer är påhittade.":
        "The company, the people and all numbers are invented.",
    "Nordvik bokför allt i en verifikationsserie, A.":
        "Nordvik books everything in one voucher series (verifikationsserie), A.",
    "Nästa dokument": "Next document",
    "Om företaget och redovisningsvalen": "About the company and its accounting choices",
    "Organisationsnummer {0}. Momsregistreringsnummer {1}. Du bokför {2}.":
        "Organisation number {0}. VAT number {1}. You keep the books for {2}.",
    "Rättar verifikation {0}.": "Corrects voucher {0}.",
    "Rättas av verifikation {0}.": "Corrected by voucher {0}.",
    "Rättelse": "Correction (rättelse)",
    "Rättelse av {0}": "Rättelse av {0}",
    "Rättelser ger ingen XP. Totalt har du {0} XP.":
        "Corrections give no XP. You have {0} XP in total.",
    "Serie": "Series",
    "Simulatorns datum: {0}. Nya dokument kommer när du har bokfört alla dokument fram till dess. "
    "{1} dokument har inte kommit än.":
        "Simulator date: {0}. New documents arrive when you have booked every document up to "
        "that date. {1} documents have not arrived yet.",
    "Underlag: {0}. Motpart: {1}.": "Source document: {0}. Counterparty: {1}.",
    "Verifikation att rätta": "Voucher to correct",
    "Verifikation {0}": "Voucher (verifikation) {0}",
    "Verifikationen balanserar inte: summa debet {0} och summa kredit {1} skiljer sig med {2}. Ett "
    "bokföringsprogram tar inte emot en verifikation som inte balanserar, så ingenting har "
    "bokförts.":
        "The voucher does not balance: total debit (debet) {0} and total credit (kredit) {1} "
        "differ by {2}. Accounting software does not accept a voucher that does not balance, so "
        "nothing has been booked.",
    "Öppna dokument": "Open document",
    "Verifikationen har inga rader ännu.": "The voucher has no rows yet.",
    "Verifikationen saknar text. Skriv kort vad affärshändelsen gäller.":
        "The voucher has no text. Write briefly what the business event is.",
    "Datumet ligger utanför månaden du bokför.":
        "The date is outside the month you are keeping the books for.",
    "Dokumentet är redan bokfört. Rätta verifikationen i stället för att bokföra igen.":
        "The document is already booked. Correct the voucher instead of booking it again.",
    "Dokumentet finns inte i inkorgen ännu.": "The document is not in the inbox yet.",
    "Du har nått gränsen för antalet verifikationer. Återställ simulatorn för att börja om.":
        "You have reached the limit on the number of vouchers. Reset the simulator to start over.",
    "Ny": "New",
    "Bokförd": "Booked",
    "Rättad": "Corrected",
    "Dokument": "Document",
    "Motpart": "Counterparty",
    "Status": "Status",
    # Simulator reports (D5.4)
    "Balanser med minustecken är kreditsaldon.":
        "Balances with a minus sign are credit balances (kreditsaldon).",
    "Balansräkning": "Balance sheet (balansräkning)",
    "Balansräkningen balanserar inte.": "The balance sheet does not balance.",
    "Balansräkningen balanserar: tillgångarna är lika stora som eget kapital och skulder.":
        "The balance sheet balances: assets equal equity and liabilities.",
    "Huvudbok": "General ledger (huvudbok)",
    "Ingående balans": "Opening balance (ingående balans)",
    "Intäkter visas med plustecken och kostnader med minustecken.":
        "Revenue is shown with a plus sign and expenses with a minus sign.",
    "Moms att betala": "VAT to pay (moms att betala)",
    "Moms att få tillbaka": "VAT to get back (moms att få tillbaka)",
    "Momsrapport": "VAT report (momsrapport)",
    "Momsrapporten gäller månadens verifikationer utom momsomföringen.":
        "The VAT report covers the month's vouchers except the VAT transfer (momsomföring).",
    "Periodens resultat": "Result for the period",
    "Periodens resultat ingår i Årets resultat, eftersom inget bokslut är gjort.":
        "The result for the period is included in Årets resultat, because no year end closing "
        "(bokslut) has been made.",
    "Resultat efter finansiella poster":
        "Result after financial items (resultat efter finansiella poster)",
    "Råbalans": "Trial balance (råbalans)",
    "Rörelseresultat": "Operating result (rörelseresultat)",
    "Summa debet och summa kredit skiljer sig åt.": "Total debit and total credit differ.",
    "Summa debet är lika med summa kredit.": "Total debit equals total credit.",
    "Summa rörelser": "Total movements",
    "Utgående balans": "Closing balance (utgående balans)",
    "Verifikationslista": "Voucher list (verifikationslista)",
    "Visa": "Show",
    "Inkorg": "Inbox (inkorg)",
    "Rapporter": "Reports",
    "Ver": "Ver",
    "Post": "Item",
    "Fält": "Field (fält)",
}
