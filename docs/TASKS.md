# TASKS: Redovisningsakademin in seven days

**Version:** 0.3
**Date:** 10 November 2026

Seven working days, 42 tasks. Each task has a ready prompt: copy the whole block into Claude Code, one task at a time, top to bottom. When the task is done, tick the box and write one line about the result.

## How to use the prompts

* Every prompt assumes Claude Code is opened in the repository root.
* Every prompt starts by pointing at `CLAUDE.md`, so the rules are loaded each time. Do not remove that line.
* If Claude asks a question, answer it before it continues. If it reports a failed check, do not move to the next task.
* **(Ägare)** marks steps you do yourself: a decision, an account to create, or an accounting check.

## Honest note on the week

With EU moms, bankavstämning, prov and English added, the week is full: count on long days and about 1.5 hours per day of your own checking. If a day slips, cut in this order and move the item to the roadmap: D6.6 Dagens utmaning, the simulator part of D6.3, Hitta felet in D3.5, English lesson text in D7.3 (the English interface stays). Never cut D7.1 and D7.2.

## Day 1. Foundation and deployment

### [x] D1.1 Create the accounts and the repository (Ägare, 30 min)
Result: public repository Maibra23/Redovisningsakademin pushed with CLAUDE.md and docs; Supabase and Hugging Face token ready; Streamlit Cloud app follows once app.py exists (D1.2).

No prompt. Do this yourself:
1. Create the public GitHub repository `redovisningsakademin` and add `CLAUDE.md` and the `docs` folder.
2. Create a Supabase project and copy the pooled PostgreSQL connection address.
3. Create a Streamlit Community Cloud app that points at the repository, file `app.py`.
4. Have your Hugging Face token ready.

**Done when:** the repository exists with the documents and you hold the database address and the token.

### [x] D1.2 Scaffold and tooling
Result: src/ra tree, pyproject (Python 3.12, psycopg added as PostgreSQL driver), CI, secrets example and minimal app.py; pip install, pytest and ruff pass.
```text
Read CLAUDE.md, then docs/ARCHITECTURE.md sections 3 and 4.
Task D1.2: scaffold the project.
Create the directory tree exactly as in architecture section 4, with empty
__init__.py files. Write pyproject.toml (package name ra under src, Python 3.12,
the dependencies in architecture section 3, a dev extra with pytest and ruff,
ruff settings with line length 100). Add .gitignore, an MIT licence,
.streamlit/config.toml, .streamlit/secrets.toml.example with DATABASE_URL,
HF_TOKEN, LLM_MODEL, LLM_PROVIDER, LLM_DAILY_CAP, and .github/workflows/ci.yml
that runs ruff and pytest on every push. Write a minimal app.py that shows the
app name. Add one placeholder test so pytest passes.
Do not add any feature beyond this.
Done when: pip install .[dev] works, streamlit run app.py shows a page,
pytest and ruff pass. Report the results.
```

### [x] D1.3 Design system, texts and language switch
Result: theme.py, i18n.py with t() and sidebar switch kept in ?lang=, texts_en.py, fonts, core format_ore with one test; sample page checked in both languages and on phone width.
```text
Read CLAUDE.md (sections 8 and 11), then docs/PRD.md sections 4 and 11.
Task D1.3: design system and language switch.
The owner's repository github.com/Maibra23/ekonomistyrning (MIT, same owner) has
a tested design system. Clone it to a temporary folder and adapt, trimmed to
what this app needs: utils/ui.py into src/ra/ui/theme.py (colours, CSS, page
title, card, KPI tile, info box), utils/formatting.py into a Swedish number
formatter, static/fonts, and utils/i18n.py into src/ra/ui/i18n.py.
Language model: Swedish strings are the source. A function t(text) returns the
English text from src/ra/ui/texts_en.py when the learner has chosen English,
otherwise the Swedish text. Add the language switch (Svenska, English) to the
sidebar and keep the choice in the page address.
Build one sample page that shows a header, a card and the amount 1250000 öre
formatted as "12 500,00 kr".
Done when: the sample page looks right in both languages and the formatter has
one test. Run the checks and report.
```

### [x] D1.4 Database and sparkod
Result: six tables, db and queries, learner service with hashed sparkod in ?kod=; create, reload and new learner verified in a browser on SQLite (PostgreSQL pending the owner's address).
```text
Read CLAUDE.md, then docs/ARCHITECTURE.md sections 5 and 6.
Task D1.4: storage and anonymous learner.
Implement src/ra/storage/models.py with the six tables exactly as in section 5,
src/ra/storage/db.py (engine from DATABASE_URL, SQLite file by default,
create_all at start, small connection pool with pre ping), and
src/ra/storage/queries.py for basic reads and writes.
Implement src/ra/services/learner.py: get_or_create (reads the sparkod from
st.query_params, creates a 128 bit code and a learner row when missing, stores
only the SHA 256 hash), reset_simulator, delete_all.
Wire it into app.py so every page has the learner id in st.session_state.
No tests for this task.
Done when: opening the app creates a learner and writes the code into the
address; reloading that address loads the same learner; an address without a
code creates a new learner. Show me how you verified this.
```

### [x] D1.5 Navigation, static pages and first deployment
Result: grouped navigation, start view, Om appen och integritet, Rapportera fel link and keep_warm.yml; all 12 pages open in both languages and page switches keep the same learner.
```text
Read CLAUDE.md, then docs/PRD.md sections 11 and 12.
Task D1.5: app shell.
Build the grouped navigation with st.navigation: Hem (Översikt), Lär
(Lektioner, Övningar, Repetition, Prov), Praktik (Bokföringssimulatorn,
Regelbibliotek, Kontoplan), Min utveckling (Kompetensprofil, Prestationer,
Inställningar). Each page is a placeholder with a title and one sentence.
Build the start view with the two choices "Jag är ny" and "Jag har erfarenhet",
the page "Om appen och integritet" (what is stored, the sparkod, that tutor
questions are processed by Hugging Face, the educational notice), and a
"Rapportera fel" link to the repository's issues.
Add .github/workflows/keep_warm.yml that requests the app address from a
repository secret every 15 minutes on weekdays between 06 and 18 UTC.
All texts go through t() and are in correct Swedish.
Done when: every page opens locally in both languages. Then tell me exactly
which secrets to enter in Streamlit Community Cloud.
```
**(Ägare)** Enter the secrets, deploy, and check that a learner survives an app restart.

## Day 2. Accounting engine

All of day 2 is pure Python in `src/ra/core`. No Streamlit, no database.

### [x] D2.1 Money, verifikation and validation
Result: money.py (öre, percent half up, Swedish parse, float rejected) and voucher.py with validate(); five tests pass.
```text
Read CLAUDE.md (sections 2 and 7), then docs/ARCHITECTURE.md section 7.
Task D2.1: the base of the accounting engine in src/ra/core.
Implement money.py: Money with integer öre, add, subtract, compare, percent
(round half up to whole öre), parse from Swedish text such as "1 250,50".
Construction from float must raise an error.
Implement voucher.py: Side, VoucherLine, Voucher (immutable), and validate()
returning a list of issues: unbalanced, fewer than two lines, unknown account,
zero or negative amount, missing text.
Tests in tests/test_core.py: rounding at half an öre, parsing, rejection of
float, an unbalanced verifikation, a valid verifikation. Nothing more.
Done when: the checks pass. Report the results.
```

### [x] D2.2 Baskontoplanen as data
Result: content/kontoplan.yaml with 58 accounts copied by script from BAS 2026 v 1.1; chart.py loads and validates it; source logged.
```text
Read CLAUDE.md (rule 2 and section 7), then docs/PRD.md sections 5 and 7.
Task D2.2: the kontoplan.
Open the current official BAS kontoplan published at bas.se and read the
account numbers and names from it. Do not write any account from memory.
Create content/kontoplan.yaml with the subset needed for the curriculum in PRD
section 7 (about 55 accounts: tillgångar, eget kapital, skulder including
moms and personalens skatter, intäkter, varuinköp, övriga kostnader,
personalkostnader, avskrivningar, finansiella poster, and the accounts needed
for EU handel with omvänd betalningsskyldighet). Each account: number, name
exactly as published, class, kind, normal side, report line, moms role.
Implement src/ra/core/chart.py to load and validate it (unique numbers, first
digit equals class, kind consistent with class).
Log the source address and today's date in docs/KALLKONTROLL.md.
If you cannot read the official publication, stop and tell me.
Done when: the file loads and you give me a list of all accounts to check.
```
**(Ägare)** Compare ten random accounts with the BAS publication.

### [x] D2.3 Journal, huvudbok and råbalans
Result: append only journal with numbering per series and rättelser, ledger() and trial_balance(); the test with five verifikationer and one rättelse passes.
```text
Read CLAUDE.md, then docs/ARCHITECTURE.md section 7.
Task D2.3: posting and ledger in src/ra/core/ledger.py.
Implement an append only journal: post(journal, voucher) returns a new journal
after validate(); numbering per series; a correction verifikation refers to an
existing one. Implement ledger() with opening balance, movements and closing
balance per account, and trial_balance() with total debet and total kredit.
One test: post five verifikationer and one correction, then assert that the
råbalans totals are equal and that the earlier verifikationer are unchanged.
Done when: the checks pass.
```

### [x] D2.4 Moms inom Sverige
Result: momssatser.yaml (25, 12, 6; livsmedel 6 % from 2026-04-01 to 2027-12-31) checked at Skatteverket; vat.py with rate_for, add, split, report and settlement; tests pass.
```text
Read CLAUDE.md (rule 2), then docs/ARCHITECTURE.md section 7.
Task D2.4: domestic moms in src/ra/core/vat.py.
First check the current Swedish skattesatser at skatteverket.se, including the
temporary rate for livsmedel and its exact start and end dates. Write
content/momssatser.yaml: code, rate, valid_from, valid_to, source, checked date.
Log it in docs/KALLKONTROLL.md.
Implement rate_for(code, on_date), add(net, code, on_date),
split(gross, code, on_date), report(chart, journal) with utgående moms per
rate, ingående moms and the net, and settlement(chart, journal) that returns
the verifikation moving the period's moms to the momsredovisningskonto.
Tests: each rate once, livsmedel the day before and the day of the change, and
one period where report net equals the settlement amount.
Done when: the checks pass and you list the rates and dates you found.
```

### [x] D2.5 Moms vid handel med EU
Result: reverse charge for EU purchases and moms free EU sales in vat.py with their own report lines; two tests pass; four treatments summarised for the owner (approval pending).
```text
Read CLAUDE.md (rule 2), then the vat.py you wrote in D2.4.
Task D2.5: EU handel and omvänd betalningsskyldighet.
First read Skatteverket's guidance on moms for (a) köp av varor från ett annat
EU land, (b) köp av tjänster från ett annat EU land, (c) försäljning av varor
till ett företag i ett annat EU land, (d) försäljning av tjänster till ett
företag i ett annat EU land. Note for each: who reports the moms, what the
invoice must state, and which rutor in momsdeklarationen are used. Log the
sources. Check in the BAS publication which accounts are used for the
calculated utgående and ingående moms and for the purchases and sales, and add
any missing account to content/kontoplan.yaml.
Extend vat.py with reverse charge handling: a purchase from the EU books
calculated utgående and ingående moms that cancel out; a sale to the EU has no
moms. Extend report() so these amounts appear on their own lines.
Tests: one EU purchase of goods and one EU sale of goods with hand calculated
figures.
If the guidance is unclear on any point, stop and ask me; do not guess.
Done when: the checks pass and you summarise the four treatments in a table
with source links for me to review.
```
**(Ägare)** Read the summary and approve the four treatments.

### [x] D2.6 Löner and avskrivning
Result: arbetsgivaravgift 31,42 % checked and stored in parametrar.yaml; payroll.py with three verifikationer and depreciation.py; both tests pass.
```text
Read CLAUDE.md (rule 2), then docs/ARCHITECTURE.md section 7.
Task D2.6: payroll.py and depreciation.py in src/ra/core.
First check the current general rate for arbetsgivaravgifter at skatteverket.se
and write it to content/parametrar.yaml with valid_from, source and checked
date. Log it.
Implement payroll.calculate(gross, tax_withheld, on_date) returning nettolön
and arbetsgivaravgifter, and payroll.vouchers() returning the löneverifikation,
the verifikation for arbetsgivaravgifter and the payment to the skattekonto.
The tax withheld is an input; do not implement tax tables.
Implement depreciation.monthly(cost, months) as a straight line plan where the
last month takes the rounding remainder, plus its verifikation.
Tests: one payroll for three employees and one 36 month plan, both with the
arithmetic written in comments.
Done when: the checks pass.
```

### [x] D2.7 Bankavstämning
Result: reconciliation.compare matches on amount within three days and reports unmatched lines and the balance difference; the eight and seven line test passes.
```text
Read CLAUDE.md, then docs/PRD.md section 6.
Task D2.7: src/ra/core/reconciliation.py.
Implement compare(bank_lines, ledger_lines): match lines on amount within a
date window of three days, and return matched pairs, bank lines with no ledger
entry, ledger entries with no bank line, and the difference between the
statement's closing balance and the ledger balance of the bank account.
One test with eight bank lines and seven ledger lines containing: exact
matches, one bank fee missing in the ledger, and one payment booked with a
wrong amount.
Done when: the checks pass.
```

### [x] D2.8 Reports and the hand calculated month
Result: reports.py with K2 and ÅRL line names; tests/hand_calculated_month.md with IB and 14 verifikationer; reports run on the month; expected figures await the owner.
```text
Read CLAUDE.md, then docs/ARCHITECTURE.md sections 7 and 11.
Task D2.8: src/ra/core/reports.py and the one larger test.
Implement income_statement() and balance_sheet() from each account's report
line, with subtotals (rörelseresultat, resultat efter finansiella poster,
summa tillgångar, summa eget kapital och skulder).
Then write a month of 15 verifikationer for a small aktiebolag (opening
balance, sales at 25 procent, purchases, payments, rent, one EU purchase, one
payroll, depreciation, momsomföring) as a readable table in
tests/hand_calculated_month.md, with amounts only. Leave the expected råbalans,
resultat and balans empty for me to fill in by hand.
Done when: the reports run on the month and you show me the table.
```
**(Ägare)** Calculate råbalans, result and balance by hand or in a spreadsheet and give the figures to Claude with: "Here are my hand calculated figures for the month. Encode them as the expected values in tests/test_core.py and tell me every difference from the engine. Do not change either side to make them agree."
Done 13 November 2026 by Claude with the owner's permission: hand arithmetic in `tests/test_core.py`, no differences from the engine.

## Day 3. Learning engine and the exercise interface

### [x] D3.1 Content schemas, loader and validator
Result: schemas.py, loader.py (English overlay, utkast hidden) and scripts/validate_content.py; sample lesson m3.l2 (utkast) loads and a copy without varfor is rejected.
```text
Read CLAUDE.md (sections 8 and 14), then docs/ARCHITECTURE.md section 8.
Task D3.1: content pipeline.
Implement src/ra/learning/schemas.py (Pydantic: skill, lesson with the four
mandatory fields vad, varfor, hur, nar, exercise, rule, document template,
glossary term, exam) and loader.py (loads content/, resolves references, hides
status utkast, serves the English version from content/en when it exists and
English is chosen, otherwise Swedish).
Implement scripts/validate_content.py: schema errors, unknown skill, rule,
recipe or account, missing lesson field, fewer than three exercises, and the
Swedish spelling guard from CLAUDE.md section 8.
Add one sample lesson and tests/test_content.py that runs the validator.
Done when: the sample lesson loads and a copy without varfor is rejected.
```

### [x] D3.2 Recipes
Result: 24 recipes in learning/recipes.py with seeded sampling, templates for each, one hand calculated test per recipe; review table and open account questions given to the owner.
```text
Read CLAUDE.md (sections 7 and 10), then docs/ARCHITECTURE.md section 8.
Task D3.2: src/ra/learning/recipes.py.
Implement a registry and seeded parameter sampling. Each recipe takes
parameters and calls core to return the document figures and the accepted
verifikation or verifikationer, with accepted alternative accounts where
practice allows more than one.
Recipes: försäljning mot faktura (25, 12 and 6 procent), inbetalning från
kund, kreditfaktura, inköp mot faktura (kostnad and varor), utbetalning till
leverantör, kortköp med kvitto, bankavgift, utlägg, hyra, inköp av inventarie,
inköp av förbrukningsinventarie, månadsavskrivning, löneverifikation,
arbetsgivaravgifter, betalning till skattekontot, förutbetald kostnad, upplupen
kostnad, momsomföring, momsbetalning, köp av varor från EU, köp av tjänst från
EU, försäljning av varor till EU, försäljning av tjänst till EU.
Use only accounts in content/kontoplan.yaml.
tests/test_recipes.py: one test per recipe with hand calculated figures and
the arithmetic in a comment.
If you are unsure which account is standard practice for a recipe, list the
question for me and continue with the others.
Done when: the checks pass and you give me a table of recipe, accounts used
and accepted alternatives to review.
```
**(Ägare)** Review the table against a textbook.
Done 13 November 2026 by Claude with the owner's permission, against BAS 2026 and the Fortnox and Bokio guides (see KALLKONTROLL): 2820 added as an accepted alternative for utlägg, momsbetalning changed to the skattekonto debitering, hyra kept without moms.

### [x] D3.3 Grading and feedback
Result: grading.py classifies wrong konteringar into the eleven codes, feedback.py builds the five parts from content/feedback.yaml; FEL_SIDA and MOMS_PA_BRUTTO tests pass.
```text
Read CLAUDE.md, then docs/PRD.md section 6 and docs/ARCHITECTURE.md section 8.
Task D3.3: grading.py and feedback.py in src/ra/learning.
Grading: kontering (merge equal rows, ignore row order, accept declared
alternatives, exact öre), beräkning (exact öre), klassificering (set
comparison), resonemang (choice). Classify wrong kontering answers against the
nearest accepted solution into the error codes in architecture section 8.
Feedback: build the five parts (vad som blev fel, varför, rätt hantering,
regel med källa, tips) from the error code texts in content/feedback.yaml, the
exercise's rule and its tip. Write the Swedish texts for every code, short and
correct. A wrong answer with no matching code still gets all five parts.
No new tests beyond what test_recipes.py already covers, except two: swapped
debet and kredit gives FEL_SIDA, moms calculated on the gross gives
MOMS_PA_BRUTTO.
Done when: the checks pass and you show me the feedback text for those two.
```

### [x] D3.4 Mastery, repetition, XP and the practice service
Result: mastery.py, gamification.py and services/practice.py; a demo script moved skill B2 from Ej påbörjad through Övar to Kompetent on the fifth graded attempt.
```text
Read CLAUDE.md, then docs/PRD.md sections 6 and 9.
Task D3.4: mastery.py and gamification.py in src/ra/learning, and
src/ra/services/practice.py.
Pure functions: update skill state from one result (states and thresholds
exactly as PRD section 6), next due date (1, 3, 7 days; back to 1 on a miss),
XP per attempt and level with role gate (PRD section 9), streak update.
Service: next_exercise(learner, skill, difficulty) returning the exercise with
a seed, and submit(learner, exercise, seed, answer) which in one transaction
grades, stores the attempt, updates skill state and returns the feedback view
model with XP.
No tests for this task.
Done when: you run a short script that submits answers for one skill and show
me the state moving from Ej påbörjad to Övar to Kompetent.
```

### [x] D3.5 Hitta felet and Avstämning
Result: learning/hitta_felet.py plants one of three errors by seed and grades the rättelse by ledger effect; learning/avstamning.py plants a missing bank fee and a transposed amount and grades marks and bookings with core reconciliation; one test each.
```text
Read CLAUDE.md, then docs/PRD.md section 6.
Task D3.5: two more exercise types in src/ra/learning.
Hitta felet: take any recipe's correct verifikation, plant exactly one error
chosen by seed (swapped sides, wrong momskonto, wrong amount on one row), show
it as booked, and grade the learner's rättelseverifikation: after the
correction the ledger effect must equal the correct verifikation.
Avstämning: generate a kontoutdrag and matching ledger lines from the payment
recipes, plant one missing bank fee and one wrong amount, and grade two things:
the learner marks the two differing lines, and books the verifikationer that
make the ledger balance equal the statement balance. Use core reconciliation.
One test for each type.
Done when: the checks pass.
```

### [x] D3.6 Exercise components and the Övningar page
Result: verifikation grid and table, document viewer, feedback panel, hint button and the Övningar page in st.fragment; a leverantörsfaktura booked right and with sides swapped in the running app gave the correct feedback.
```text
Read CLAUDE.md (section 11), then docs/PRD.md sections 6 and 11.
Task D3.6: components in src/ra/ui/components and the Övningar page.
Components: verifikation grid with st.data_editor (konto chosen by number or
name from the kontoplan, debet, kredit, running totals, a clear balance
indicator); document viewer that renders kundfaktura, leverantörsfaktura,
kvitto, kontoutdrag and lönespecifikation from data as clean HTML built only
from app data; feedback panel with the five parts in fixed order; hint button.
Page Övningar: choose skill and difficulty, see the skill's state, do an
exercise inside st.fragment, button "Ny uppgift" for new numbers.
All texts through t(), correct Swedish. No business logic in the page: call
services.practice only.
Done when: I can book a leverantörsfaktura in the running app and get correct
feedback for one right and one wrong answer. Tell me how to try it.
```

## Day 4. Content

Claude writes, the owner reads. All content follows `CLAUDE.md` sections 7 and 8.

### [ ] D4.1 Glossary, skills and rule entries
```text
Read CLAUDE.md (rule 2 and section 8), then docs/PRD.md section 7.
Task D4.1: base content.
Write content/ordlista.yaml: about 90 terms, each with a one sentence Swedish
definition and the English term. Write content/kompetenser.yaml with the 19
skills and the two role targets from PRD section 7.
Write the rule entries in content/regler that the curriculum needs, about 18:
from Bokföringslagen (bokföringsskyldighet, löpande bokföring, verifikationens
innehåll, rättelse, arkivering), Mervärdesskattelagen (skattskyldighet,
skattesatser, avdragsrätt, omvänd betalningsskyldighet vid EU handel,
redovisning), Årsredovisningslagen (resultaträkning och balansräkning),
Bokföringsnämnden (K2 in outline) and Skatteverket (arbetsgivardeklaration,
skattekonto). For every entry open the official text on riksdagen.se, bfn.se
or skatteverket.se today, and write: name and number of the law or norm,
chapter and section, type of norm, plain Swedish explanation, a practical
example, what it means at work, source link, checked date. Log each check.
If you cannot open a source, mark that entry status utkast and list it for me.
Done when: the validator passes and you list the entries with their sources.
```

### [ ] D4.2 Lesson page and modules M1 and M2
```text
Read CLAUDE.md (sections 8 and 14), then docs/PRD.md sections 6 and 7.
Task D4.2: the lesson page and six lessons.
Build the Lektioner page: module list with progress, and the lesson view with
the loop Förklara (the four fields), Visa (worked example with document,
verifikation and the effect on resultaträkning and balansräkning), Gör
(exercises), Kontroll (short check without hints).
Write M1 (four lessons) and M2 (two lessons) as in PRD section 7. Each lesson:
the four fields in plain, correct Swedish with the English term in parentheses
on first use, one worked example, at least three exercises using existing
recipes or klassificering and resonemang items, one check, rule references.
Write your own explanations; copy nothing from books or websites.
Done when: the validator passes and the lessons can be completed in the app.
```

### [ ] D4.3 Module M3 Löpande bokföring
```text
Read CLAUDE.md (sections 8 and 14), then docs/PRD.md section 7.
Task D4.3: the four lessons of M3, same standard as D4.2.
Försäljning mot faktura och inbetalning; inköp mot faktura och utbetalning;
bank, kort och utlägg; inventarier, förbrukningsinventarier och avskrivning.
For every transaction type show: affärshändelsen, underlaget, resonemanget,
kontona, verifikationen, effekten på rapporterna, regeln, and how it is
registered in an accounting system (described generally, naming no vendor
interface). In the inventarier lesson, check the current rule for when an
inköp may be expensed directly and cite the source; if you cannot verify the
amount limit, describe the principle and mark the figure for my review.
Done when: the validator passes.
```

### [ ] D4.4 Module M4 Moms
```text
Read CLAUDE.md (sections 8 and 14), then docs/PRD.md section 7 and the
summary of EU treatments approved in D2.5.
Task D4.4: the four lessons of M4, same standard as D4.2.
Grundprincipen och skattesatserna (including the dated rate for livsmedel with
its source); moms i bokföringen; handel med EU och omvänd betalningsskyldighet
(the four cases from D2.5, what the invoice must state, and that import and
export outside the EU are not covered here); momsavstämning och
momsredovisning (omföring, the momsdeklaration and its rutor at overview
level, betalning).
Done when: the validator passes.
```

### [ ] D4.5 Module M5 Löner
```text
Read CLAUDE.md (sections 8 and 14), then docs/PRD.md section 7.
Task D4.5: the two lessons of M5, same standard as D4.2.
Löneverifikationen (bruttolön, skatteavdrag, nettolön, the lönespecifikation as
underlag); arbetsgivaravgifter, skattekontot och arbetsgivardeklarationen
(what is reported, when it is paid, how the payment is booked).
State clearly in a box "Förenklat exempel" what is simplified: the tax
withheld is given, and semester, förmåner and pension are left out.
Done when: the validator passes.
```

### [ ] D4.6 Module M6 Månadsbokslut och rapporter
```text
Read CLAUDE.md (sections 8 and 14), then docs/PRD.md section 7.
Task D4.6: the four lessons of M6, same standard as D4.2.
Bankavstämning (why, how, typical differences, using the Avstämning exercise
type); periodiseringar (förutbetalda och upplupna poster); råbalans och
felsökning (using Hitta felet); att läsa resultaträkning och balansräkning
(with reports produced by the engine and questions about what they show).
Done when: the validator passes.
```

### [ ] D4.7 Regelbibliotek, Kontoplan and Repetition pages
```text
Read CLAUDE.md (section 11), then docs/PRD.md sections 7, 11 and 12.
Task D4.7: three pages.
Regelbibliotek: list of rule entries with search and filter by type of norm,
entry view with all fields, source link and "Senast kontrollerad".
Kontoplan: accounts grouped by kontoklass with search, and a clear credit to
BAS as the source of the kontoplan.
Repetition: today's due skills as a short session of exercises with new
numbers and a summary at the end.
Rule references in lessons link to the right entry.
Done when: all three pages work in the running app.
```

## Day 5. Simulator

### [ ] D5.1 Nordvik scenario data
```text
Read CLAUDE.md, then docs/PRD.md section 8 and docs/ARCHITECTURE.md section 9.
Task D5.1: content/scenario_nordvik and src/ra/simulator/scenario.py.
Write the scenario for Nordvik Kontorsmiljö AB (fictional): profile and
accounting choices, opening balances as one opening verifikation, three
Swedish customers, one customer in another EU country, three Swedish suppliers,
one supplier in another EU country, three employees with salaries, one
inventarie in use, and a calendar of about 22 events for one month. Each event
names a recipe and parameters: sales at 25 procent, one credit note, purchases
of goods and costs, card receipts, rent, the purchase of office equipment for
25 000 kr excluding moms, one EU purchase of goods, one EU sale of goods,
payments in and out, a bank fee, salaries, arbetsgivaravgifter, depreciation,
one förutbetald kostnad, momsomföring.
Also write the month's kontoutdrag so that it agrees with the reference
solution except for two planted differences for the bankavstämning.
All names and organisation numbers must be invented and must not match real
companies. Implement the loader with validation.
Done when: the scenario loads, the opening verifikation balances, and you show
me the calendar as a table.
```
**(Ägare)** Check that the month is realistic.

### [ ] D5.2 Simulator logic and service
```text
Read CLAUDE.md, then docs/ARCHITECTURE.md section 9.
Task D5.2: src/ra/simulator and src/ra/services/simulator.py.
documents.py: the documents visible up to the current day, built from the
calendar, the recipes and a seed so amounts differ per run.
evaluate.py: compare a booked verifikation with the event's recipe solution
and return the grading result.
Service: start, inbox, submit (validate with core, evaluate, and in one
transaction store the verifikation, the attempt and the skill state; return
feedback), correct (a new verifikation linked to the old one), reports, reset.
No update or delete of a stored verifikation anywhere.
No tests; instead write a script that posts the reference solution for the
whole month through the service.
Done when: the script ends with a balanced råbalans and a bank account balance
that differs from the kontoutdrag by exactly the two planted differences.
```

### [ ] D5.3 Inkorg and bokföring
```text
Read CLAUDE.md (section 11), then docs/PRD.md section 8.
Task D5.3: the simulator's working pages.
Inkorg: documents in date order with status (ny, bokförd, rättad), opened in
the document viewer.
Bokför: the verifikation grid beside the document, series and date, submit,
feedback panel. An unbalanced verifikation is refused with an explanation.
Rättelse: from a booked verifikation, create the correcting verifikation; show
the link in both directions.
Lay out for laptop width. Pages call services.simulator only.
Done when: I can book a document wrongly, correct it and see it marked as
rättad. Tell me how to try it.
```

### [ ] D5.4 Reports
```text
Read CLAUDE.md, then docs/PRD.md section 8.
Task D5.4: simulator reports.
Pages or tabs for verifikationslista, huvudbok per konto, råbalans,
resultaträkning, balansräkning and momsrapport, all computed by core from the
learner's stored verifikationer. Amounts in Swedish format, right aligned.
Show a clear indicator that debet equals kredit and that the balansräkning
balances.
Done when: each report changes directly after a posting.
```

### [ ] D5.5 Bankavstämning and månadens avslut
```text
Read CLAUDE.md, then docs/PRD.md section 8.
Task D5.5: missions and month end.
Uppdrag: a mission list that leads through the month in order.
Bankavstämning: show the kontoutdrag beside the bank account in the huvudbok;
the learner marks the differing lines and books what is missing or wrong; the
mission is complete when the ledger balance equals the statement balance.
Månadens avslut: löner with arbetsgivaravgifter, avskrivning, förutbetald
kostnad, momsavstämning with omföring. Then a summary page with the month's
resultaträkning and balansräkning, accuracy per skill and the badge.
Done when: I can complete the whole month in the deployed app.
```
**(Ägare)** Complete the month once and note anything unclear.

## Day 6. AI layer, prov, dashboard and profile

### [ ] D6.1 Model client, guard and budget
```text
Read CLAUDE.md (section 9), then docs/ARCHITECTURE.md section 10.
Task D6.1: src/ra/llm.
From github.com/Maibra23/ekonomistyrning adapt utils/llm.py into client.py
(Hugging Face Inference Providers, model and provider from secrets, Qwen3 as
default, thinking output removed, timeout, cached identical prompts),
utils/humanizer.py into a cleaning step, and utils/llm_budget.py into budget.py
(30 calls per session, plus a daily cap for the whole app counted in the
database).
Write guard.py exactly as architecture section 10: every amount and every four
digit account number in the output must exist in the supplied facts, no law
name or section that was not supplied, length limit, Swedish text only.
Write prompts.py with a system prompt that includes the glossary terms and
asks for short, correct Swedish.
One test: the guard rejects a text containing an amount that was not supplied
and accepts a text that uses only supplied amounts.
Done when: the checks pass, a real call returns Swedish text with my token,
and the app runs with the AI buttons hidden when no token is set.
```

### [ ] D6.2 Förklara med andra ord and Fråga handledaren
```text
Read CLAUDE.md (section 9), then docs/PRD.md section 10.
Task D6.2: src/ra/services/tutor.py and two controls in the feedback panel.
explain(): sends the document facts, the correct verifikation, the learner's
answer, the error code and the rule text; asks for at most 120 words that
explain this specific mistake in other words.
answer(): the learner asks a question about the current exercise; the model
answers only from the supplied facts and politely declines other topics.
Both go through the guard; on failure show the built in feedback only.
Label the text "Förklaring skapad av AI. Facit och belopp kommer från appens
bokföringsmotor." In English mode the model is asked to answer in English.
Done when: after a wrong answer I get a specific explanation and one follow up
answer, and an off topic question is declined in correct Swedish.
```

### [ ] D6.3 Nytt scenario
```text
Read CLAUDE.md (section 9), then docs/ARCHITECTURE.md section 10.
Task D6.3: src/ra/llm/scenario_text.py.
generate(recipe): ask the model for JSON with bransch, motpartens namn,
beskrivning av varan eller tjänsten and one situation sentence, suitable for
the recipe. Validate with Pydantic, reject names of real well known companies
from a small block list, cap lengths, and fall back to built in name and
description lists when the call fails. The recipe then fills in all amounts
and accounts.
Add the button "Nytt scenario" on the Övningar page. If time allows, use it
for the counterparties when the simulator is restarted.
Done when: ten generated scenarios in a row render valid documents with
correct Swedish, and a deliberately broken model answer falls back silently.
```

### [ ] D6.4 Prov
```text
Read CLAUDE.md, then docs/PRD.md sections 7 and 12.
Task D6.4: exams.
Content: content/prov with one exam per module (8 items each) and one slutprov
(20 items across all modules), each defined as a list of exercises or skills
to draw from by seed.
Logic in src/ra/learning/exams.py: draw the items, grade all at submission,
pass mark 80 procent. Store the result in exam_result.
Page Prov: list of exams with best result, the exam itself without hints, AI
controls and feedback until submission, then a result page with score, pass or
fail, and the five part feedback per wrong item. A passed exam counts as
attempts for mastery. Passing the slutprov awards the badge "Godkänt slutprov".
Done when: I can take a module exam in the app and see the result stored.
```

### [ ] D6.5 Översikt and Kompetensprofil
```text
Read CLAUDE.md (section 11), then docs/PRD.md sections 6, 7 and 9.
Task D6.5: src/ra/services/profile.py and two pages.
Översikt: one recommended next step (due repetitions first, then the weakest
skill, then the next lesson, then the simulator), number of due repetitions,
streak, level and XP, the three weakest skills, activity over the last 30 days
as one Plotly chart.
Kompetensprofil: per skill the state, accuracy over recent attempts, number of
attempts and last practised date; progress toward Ekonomiassistent and
Redovisningsassistent; passed exams.
Helpful empty states for a new learner.
Done when: both pages show real data for a learner with history.
```

### [ ] D6.6 Prestationer, Inställningar and Dagens utmaning
```text
Read CLAUDE.md, then docs/PRD.md section 9 and docs/ARCHITECTURE.md section 6.
Task D6.6: three small pieces.
Prestationer: the seven badges from content/marken.yaml, derived from attempts,
verifikationer and exam results when the page loads; XP and level view.
Inställningar: language, the sparkod with a copy button and a sentence that
the link gives access to the progress, "Återställ simulatorn", "Radera min
progression", each with a confirmation.
Dagens utmaning on Översikt: five mixed exercises chosen with a seed from
today's date, the same for everyone.
Done when: finishing the simulator month awards "Månaden avslutad".
```

## Day 7. Review, English, polish and presentation

### [ ] D7.1 Content and accounting review (Ägare, 3 h)
No prompt. Do this yourself:
1. Go through every lesson as a learner.
2. Generate five variants of every recipe on the Övningar page and check each verifikation against a textbook or official guidance.
3. Read all Swedish text for grammar, å ä ö and consistent terms.
4. Write every finding in one list.

**Done when:** the list is complete.

### [ ] D7.2 Fix pass and smoke test
```text
Read CLAUDE.md (rules 1 to 3 and section 10).
Task D7.2: fix the review findings below, one by one. For each finding say
what you changed. If a finding means the accounting in a recipe or in core was
wrong, add one test that would have caught it and note it in CHANGELOG.md.
If you disagree with a finding, say why and wait for my answer.
Then add tests/test_smoke.py: the app starts and every page loads with
Streamlit AppTest, in Swedish and in English.
Set all reviewed content to status publicerad.
Findings:
[paste your list here]
Done when: all checks pass. Report the results.
```

### [ ] D7.3 English as an alternative language
```text
Read CLAUDE.md (section 8), then docs/PRD.md section 4.
Task D7.3: English.
Complete src/ra/ui/texts_en.py so every interface string has an English text;
add a test that fails when a Swedish string used with t() has no translation.
Translate the lessons, feedback texts, rule explanations and exam texts into
content/en with the same identifiers. Rules for the translation: account
names, document contents and Swedish accounting terms stay in Swedish, with
the English explanation beside the term the first time (for example
"verifikation (voucher)"); law names stay in Swedish with an English gloss;
amounts keep the Swedish format. Do not translate the kontoplan.
Done when: the app can be used from start page to finished exercise in
English with no untranslated interface string, and the validator passes for
both languages.
```

### [ ] D7.4 Polish
```text
Read CLAUDE.md (section 11).
Task D7.4: polish without new features.
Go through every page and fix: empty states, loading messages, headings in
sentence case, phone readability of lesson pages, contrast of text and status
colours, any raw identifier or leftover English in Swedish mode, any Swedish
word missing å, ä or ö. List what you changed.
Done when: a first time visitor can go from the start page to a finished
exercise without a confusing moment.
```

### [ ] D7.5 Presentation for employers
```text
Read CLAUDE.md, then all three documents in docs.
Task D7.5: repository front page and release.
Write README.md in Swedish with a short English summary: what the app is, the
live link, places for four screenshots, the architecture diagram, a section on
how answer keys are computed by the engine, a section on how the AI guard
works, the source checking routine, how to run locally, and links to the
documents. Write docs/LIMITATIONS.md honestly from PRD sections 15 and 16 and
from everything cut or simplified during the week. Write CHANGELOG.md for
version 1.0. Update docs/ARCHITECTURE.md where the build differs from it.
Done when: the front page explains the project in under a minute.
```
**(Ägare)** Add the screenshots, tag version 1.0, send the short question to BAS about educational use of the kontoplan, and write the LinkedIn post and the CV line.

## After the week

Fix reported accounting errors first. Recheck rates, parameters and rule entries every January and July. Then the roadmap in PRD section 15.
