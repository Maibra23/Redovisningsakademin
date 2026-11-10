# CLAUDE.md: working rules for Redovisningsakademin

Read this file at the start of every session. Then read `docs/PRD.md`, `docs/ARCHITECTURE.md` and the current task in `docs/TASKS.md` before implementing anything.

## 1. Project in short

A free Swedish language Streamlit app that teaches extern redovisning through lessons, exercises with precise feedback and a bookkeeping simulator, using the baskontoplan (BAS). No login. The whole first version is built in seven days, so scope discipline matters as much as code quality. The repository is also a portfolio piece that employers will read.

## 2. Absolute rules

1. **Never silently change accounting rules.** A change in how the engine calculates, rounds, validates or reports needs the owner's approval and a note in `CHANGELOG.md`.
2. **Never invent legal references, rates or account numbers.** Laws, sections, rates, thresholds and BAS accounts are written only after checking the official source in the same task, and are logged in `docs/KALLKONTROLL.md`. If it cannot be checked, mark the content `status: utkast` and ask the owner.
3. **Never bypass tests.** Do not delete, skip or loosen an existing test to make a change pass. Do not change hand calculated expected figures unless the owner confirms the new figures are correct accounting.
4. **Never put business logic in presentation code.** `src/ra/ui` contains layout, widgets and calls to `services`. No calculations, no grading, no database access.
5. **Never use floats for money.** Integer öre through `Money`.
6. **Never edit or delete a posted verifikation.** Corrections are new verifikationer.
7. **Never let the language model decide.** It does not grade, calculate, pick accounts or cite rules. Its output is shown only after the guard passes.
8. **Never store personal data** and never add tracking.
9. **Never copy** text, images or interfaces from textbooks, Fortnox, Visma or other products.
10. **Stay inside the task.** No extra features, no refactoring outside the task, no new dependencies without asking.

## 3. Stack

Python 3.12, Streamlit 1.50 or later, SQLAlchemy 2, PostgreSQL through psycopg 3 (SQLite locally), Pydantic 2, PyYAML, Plotly, huggingface_hub, pytest, ruff.

## 4. Structure and layer rules

* `src/ra/core`: accounting engine. Pure Python. Imports nothing from the project, Streamlit or SQLAlchemy.
* `src/ra/learning`: content loading, recipes, grading, feedback, mastery, XP. Pure. May import `core`.
* `src/ra/simulator`: scenario, documents, evaluation. Pure. May import `core`.
* `src/ra/llm`: model client, prompts, guard, budget.
* `src/ra/storage`: models and queries. No business rules.
* `src/ra/services`: use cases. The only layer that combines the others. One call, one transaction.
* `src/ra/ui`: pages and components. Imports `services` only.
* `content`: all authored material as YAML.

Every figure shown to a learner comes from `core`. Exercise keys come from recipes that call `core`; never type a key amount into a content file.

## 5. Coding conventions

* Type hints on all functions. Immutable dataclasses for domain objects.
* Small functions with one purpose. Typed errors, never bare `Exception`.
* Code, identifiers, comments and commit messages in English. File names and identifiers in ASCII.
* Docstrings in `core` state the accounting meaning, with the Swedish term.
* No commented out code.
* Commit format: `area: summary (task id)`, for example `core: add vat settlement (D2.4)`. Small commits, one task at a time.

## 6. Naming

* `snake_case` for modules and functions, `PascalCase` for classes.
* Domain names in code are English (`voucher`, `ledger`, `trial_balance`, `vat`, `payroll`).
* Content identifiers use dots: lesson `m3.l2`, exercise `m3.l2.e1`, rule `bfl.5.7`. Skill codes as in PRD section 7.
* Amount columns end in `_ore`, dates in `_on`, timestamps in `_at`.

## 7. Accounting requirements

* Amounts are integer öre. Display through the one formatting helper: space as thousands separator, comma as decimal sign, "kr" after the amount.
* Percent calculations only through `Money.percent`, rounding half up to whole öre.
* Rates and thresholds by transaction date from `content/momssatser.yaml` and `content/parametrar.yaml`. Never a rate in code.
* Accounts only from `content/kontoplan.yaml`, with number and name exactly as in the official BAS publication.
* If two treatments are acceptable in practice, declare both as accepted and say so in the feedback.
* If a treatment depends on a company choice (faktureringsmetoden, K2), the exercise states the choice.
* If you are unsure whether a treatment is correct Swedish practice, say so and mark it `status: utkast`. Stated uncertainty is fine; confident errors are not.

## 8. Swedish language requirements

All learner facing text is Swedish and must read as written by a careful native professional.

* **Characters.** Always å, ä and ö. Never "a" or "o" as replacements, never "aa", "ae" or "oe". All files are saved as Unicode. Only file names and code identifiers are ASCII.
* **Compounds.** Write compounds as one word: leverantörsfaktura, momsredovisningskonto, arbetsgivaravgifter. No särskrivning.
* **Terms.** Use the term in `content/ordlista.yaml` and no synonym: verifikation, kontering, debet, kredit, huvudbok, råbalans, resultaträkning, balansräkning, ingående moms, utgående moms, bruttolön, nettolön, skatteavdrag, arbetsgivaravgifter. Add a term to the glossary before using a new one.
* **Grammar.** Correct gender and definiteness (en faktura, fakturan; ett konto, kontot), correct plural forms, correct word order after an opening adverbial (verb in second position).
* **Style.** Short sentences. Address the learner as "du". Active voice. Sentence case in headings (only the first word capitalised). No English words where a Swedish term exists.
* **Numbers and dates.** 12 500,00 kr. Percent written "25 procent" in running text and "25 %" in tables. Dates as "15 januari 2026".
* **English support.** The English term appears once in parentheses when a concept is introduced.
* **English as alternative language.** Every interface string goes through `t()` and has an English text in `ui/texts_en.py`. English content lives in `content/en` with the same identifiers. In English mode, account names, document contents and Swedish accounting terms stay in Swedish with the English explanation beside them; law names stay in Swedish with an English gloss. The kontoplan is never translated.
* **Dashes.** The owner does not want dash characters in running text. Never use a dash as punctuation between clauses; rewrite the sentence. A hyphen is allowed only where correct Swedish spelling requires it, for example T-konto, BAS-kontoplanen, K2-regelverket, EU-handel and e-faktura.
* **Check.** `scripts/validate_content.py` rejects content containing common ASCII misspellings of Swedish words (for example "bokforing", "forsaljning", "lon ", "ranta").

## 9. Language model rules

* The model gets facts from the engine and returns text. Prompts live in `llm/prompts.py`, with the glossary included.
* Every output passes `llm/guard.py` before display. On failure, show the built in explanation and log the failure.
* Label model text in the interface as created by AI, and state that keys and amounts come from the app's own engine.
* Respect the budget in `llm/budget.py`. Cache identical prompts.
* The app must work fully with no token. Hide the AI buttons when the model is unavailable.
* Never write lesson text, rule entries or keys with the model at run time.

## 10. Testing policy: minimal and targeted

Testing is deliberately limited in this project. Do not expand it on your own initiative.

* Write tests only for `core` and for recipes, plus the one content validation test and the one smoke test described in section 11 of the architecture document.
* One clear test per behaviour is enough. No test first requirement, no coverage target, no property based tests, no tests for pages, components, services, queries or model wording.
* A recipe test contains hand calculated figures with the arithmetic in a comment.
* When fixing an accounting bug in `core`, add one test that would have caught it.
* Before saying a task is done, run `pytest`, `ruff check .` and `python scripts/validate_content.py`, and report the real result. If something fails, say so.
* If you believe more tests are needed somewhere, suggest it in one sentence and continue; do not write them unasked.

## 11. Interface guidelines

* One main action per screen. All labels are Swedish strings passed through `t()`.
* Verifikationer always in the shared component: konto, kontonamn, debet, kredit, totals and a balance indicator.
* Amounts right aligned in the tabular font.
* Colour only for meaning, always with text or an icon.
* No animation beyond progress indicators.
* Feedback always in the feedback panel with the five parts in fixed order.
* `st.fragment` around exercise interaction.
* Learner text is never rendered as HTML.

## 12. Documentation

* Tick the task in `docs/TASKS.md` with one line about the result.
* Update `docs/ARCHITECTURE.md` when structure, tables or engine functions change.
* Add every known gap to `docs/LIMITATIONS.md`.
* Log every checked source in `docs/KALLKONTROLL.md`: date, what, where, result.

## 13. Workflow per task

1. Read the task and its "Done when" list.
2. State a short plan and the files you will touch. Ask if something is unclear.
3. Implement the smallest change that completes the task.
4. Run the three checks in section 10.
5. Summarise: what changed, check results, anything the owner must verify.

## 14. Adding a lesson or module

1. Confirm it is in PRD section 7, or propose the change first.
2. Check and add the rule entries it cites (rule 2).
3. Write the lesson file with the four fields, a worked example, at least three exercises and a check.
4. Reuse recipes; add a recipe with one test only when needed.
5. Run the validator. Set `status: publicerad` after the owner's review.

## 15. Changing the accounting engine

1. Describe the change and its accounting reason; get approval if behaviour changes.
2. Change the engine and adjust or add one test with hand calculated figures.
3. Run the checks. If the hand calculated month changes, stop and show the difference to the owner.
4. Update the architecture document and the changelog.

## 16. Adding an exercise

1. Choose skill, type and difficulty.
2. Pick an existing recipe and a realistic parameter range.
3. Write the tip and the rule reference.
4. Run the validator, which executes the recipe on sampled parameters.

## 17. Validating accounting logic

* Compare the engine's result with a hand calculation.
* After a new transaction type, check both the result effect and the balance effect against the lesson text.
* After a moms change, check that utgående minus ingående equals the settlement amount.

## 18. Commands

* Install: `pip install .[dev]`
* Run: `streamlit run app.py`
* Tests: `pytest`
* Lint: `ruff check .`
* Content check: `python scripts/validate_content.py`
