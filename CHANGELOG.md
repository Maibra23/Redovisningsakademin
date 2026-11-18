# Changelog

Notable changes, newest first. Version 1.0 is written at the end of the week (D7);
until then entries collect under "Unreleased", grouped by task.

## Unreleased

### Day 6: AI layer, prov, dashboard and profile (D6.1 to D6.6)

Added
* `src/ra/llm`: model client (Hugging Face Inference Providers, token, model and provider from the environment or secrets, Qwen3-14B as default, thinking removed, 30 second timeout, cache of identical prompts), cleaning step, guard, budget (30 calls per session, a daily cap for the app) and the system prompt with the glossary; adapted from `utils/llm.py`, `utils/humanizer.py` and `utils/llm_budget.py` in the ekonomistyrning repository. Table `llm_usage` for the daily count, `services/ai.py` as the only way to the model, and one guard test (D6.1).
* "Förklara med andra ord" and "Fråga handledaren" under the feedback of practice exercises: `services/tutor.py` builds the facts from the exercise, the learner's answer and the grader's feedback; `ui/components/tutor.py` shows the labelled AI text or the reason there is none. `SubmitResult` carries the learner's answer as text lines (D6.2).
* "Nytt scenario" on Övningar: `llm/scenario_text.py` asks the model for a story as JSON and validates it, with a built in fallback; `services/scenarios.py` draws a new instance and keeps the story; the underlag shows the story's counterparty, situation and a detail after the recipe's own description. `ai.complete` for raw structured answers, and a temperature parameter in the client (D6.3).
* Prov: `content/prov` with six module exams and the slutprov, `learning/exams.py` (draw by seed with the skills taking turns, score with the pass mark), `services/exams.py` and the Prov page. An exam may name `kompetenser` as well as `ovningar`; the pool size check moved from the schema to the loader, which also refuses a published exam that draws from draft lessons. `practice.grade_item` grades an item without storing it, and each type's correct treatment now comes from one function shared by the graders; grading itself is unchanged (D6.4).
* Översikt and Kompetensprofil from `services/profile.py`; the start page keeps the welcome as the empty state for a new learner. Queries for attempts since a date and the last attempt per skill; `practice.progress_of` and `practice.skill_view_of` are now public for the profile service (D6.5).
* Prestationer with seven märken from `content/marken.yaml` derived by `learning/badges.py` (schema `Badge` with a `villkor`), and the nivåer; Inställningar with language, the sparkod link, "Återställ simulatorn" (a new seed through `simulator.reset`) and "Radera min progression", each with a confirmation; Dagens utmaning on Översikt, five exercises drawn from the date. `simulator.month_finished` checks every stored run (D6.6).

### Day 5: simulator (D5.1 to D5.5)

Added
* `content/scenario_nordvik` and `simulator/scenario.py`: Nordvik Kontorsmiljö AB with profile and redovisningsval, parties, three employees, the opening verifikation with open invoices, a calendar of 23 events for January 2026 and the kontoutdrag with two planted differences; loader with checks and the reference month per seed, run by the content validator (D5.1).
* Recipe `upplosning_forutbetald_hyra` (debet 5010, kredit 1710, 1790 accepted) with one test and its document template, for the month's rent paid in advance last month. No existing recipe or engine rule changed; `recipes.tax_withheld`, `recipes.sample_value` and `recipes.percent_text` are now public so the scenario uses the same rules as the exercises (D5.1).
* `simulator/documents.py`, `simulator/evaluate.py`, `services/simulator.py` and `scripts/simulate_month.py`: the Inkorg, grading of bookings and rättelser, reports from the stored verifikationer, and a script that books the reference month through the service (D5.2).
* Bokföringssimulatorn page: Inkorg, Bokför and Rättelse (D5.3).
* Uppdrag, bankavstämning and month summary with the badge "Månaden avslutad"; missions in `content/scenario_nordvik/uppdrag.yaml`; `scripts/simulate_month.py` now also reconciles the bank and checks the summary (D5.5).
* Simulator reports: verifikationslista, huvudbok per konto, råbalans, resultaträkning, balansräkning and momsrapport with balance indicators (D5.4).
* `practice.record_graded`: the attempt, XP, mastery and svit writes moved out of `practice.submit` unchanged, so the simulator follows the same rules. `format_date` moved to `core/formatting.py` (still exported from `services/formatting.py`). Storage queries for the run seed in the learner's settings and for adding and reading simulator verifikationer (D5.2).

### Day 1: foundation (D1.1 to D1.5)

Added
* Repository, project scaffold, CI (ruff and pytest on every push) and the MIT licence (D1.1, D1.2).
* PostgreSQL driver `psycopg[binary]` as a dependency. It is required for SQLAlchemy to reach Supabase; recorded in `CLAUDE.md` and `docs/ARCHITECTURE.md` section 3 (D1.2).
* Design system `ui/theme.py`, `t()` and the language switch in `ui/i18n.py`, English texts, self-hosted fonts, and `core/formatting.format_ore` with one test (D1.3).
* Six tables, database engine, queries and the anonymous learner with a hashed sparkod in `?kod=` (D1.4).
* Grouped navigation, start view, "Om appen och integritet", "Rapportera fel" link, `keep_warm.yml` and `requirements.txt` for Streamlit Community Cloud (D1.5).

Fixed during day 1
* The learner was lost on page switches: Streamlit can drop query parameters when the page changes, and a missing `kod` created a new learner. `get_or_create` now writes the code from session state back into the address (D1.5).
* Fonts: the Streamlit widgets and headings used Streamlit's own font. The self-hosted Inter and IBM Plex Mono are now registered as `[[theme.fontFaces]]` in `.streamlit/config.toml` (D1.5).
* The "Rapportera fel" button in the sidebar showed white text on white; it now has a transparent background with a light border (D1.5).
* The sidebar label style also capitalised the radio options; it is now limited to the widget heading (D1.3).
* Licence metadata in `pyproject.toml` moved to the current SPDX form, which removed a setuptools warning (D1.2).

### Day 2: accounting engine (D2.1 to D2.8)

Added
* `core/money.py` and `core/voucher.py`: integer öre, percent half up, Swedish parsing, verifikation validation (D2.1).
* `content/kontoplan.yaml` with 58 accounts copied by script from BAS 2026 v 1.1, and `core/chart.py` (D2.2).
* `core/ledger.py`: append only journal, numbering per series, rättelser, huvudbok and råbalans (D2.3).
* `content/momssatser.yaml` and `core/vat.py`: rates by date including livsmedel 6 procent from 1 April 2026 to 31 December 2027, report and momsomföring (D2.4).
* Omvänd betalningsskyldighet for EU purchases and moms free EU sales, with their own report lines (D2.5).
* `content/parametrar.yaml` (arbetsgivaravgift 31,42 procent), `core/parameters.py`, `core/payroll.py` and `core/depreciation.py` (D2.6).
* `core/reconciliation.py` for bankavstämning (D2.7).
* `core/reports.py` and the hand calculated month in `tests/hand_calculated_month.md` (D2.8).

Changed
* `Money.percent` now computes with exact fractions instead of Decimal division. The rounding rule is unchanged (half up to whole öre, halves away from zero). Reason: moms inside a gross amount at 12 procent uses the rate 12/112, which Decimal cannot hold exactly, so a true half öre (for example 14 öre gross) rounded down. Found while writing `vat.split` (D2.4).

### Day 4: content (D4.1 to D4.7)

Added
* `content/ordlista.yaml` (94 terms) and 22 rule entries in `content/regler`, each checked at riksdagen.se, bfn.se or skatteverket.se on 14 November 2026 (D4.1).
* `content/moduler.yaml` and the 20 lessons of modules M1 to M6, with 94 övningar and 39 kontroll items; all lessons are status utkast pending the owner's review (D4.2 to D4.6).
* Lektioner page with module progress and the Förklara, Visa, Gör and Kontroll steps; `services/lessons.py`; `ui/components/exercise.py` shared by Övningar, lessons and Repetition; `ui/components/report_effect.py` (D4.2).
* Optional lesson field `forenkling`, shown as a "Förenklat exempel" box (D4.5).
* Regelbibliotek, Kontoplan and Repetition pages; `services/reference.py`; `practice.due_skills` (D4.7).

Changed
* `practice.next_exercise` accepts no difficulty (any level), `practice.submit` takes the attempt context, and `practice.start_exercise` starts a named exercise. No change to grading or to the accounting engine.
* Övningar now draws its exercise with the shared component; behaviour unchanged.

Fixed after the day 4 review
* The Visa tab listed every report line with "+0,00 kr"; it now shows only the lines the verifikation changes (`Money` has no truth value, so the filter now tests `amount.ore`).
* Asking for a new exercise cleared the shown tip of every open exercise, so a later answer on another exercise could earn full XP after using its tip. Only the replaced instance is cleared now, and its stored result with it.
* "Ny uppgift" and Repetition's "Nästa uppgift" used a fragment rerun that fails when the fragment is drawn during a full run; both are click callbacks now.
* Repetition says when a session is capped at ten skills instead of dropping the rest silently.
* Modules, lessons and rule entries sort in natural id order, so m10 and bfl.10.1 will not land before m2 and bfl.5.7.
* The kontoplan source block is read through `core.chart.load_chart_source` with a typed error, not parsed in the services layer.
* The English sample lesson m3.l2 now matches the revised Swedish text and rule list.

### Day 3: learning engine and exercise interface (D3.1 to D3.6)

Added
* `learning/schemas.py`, `learning/loader.py` and `scripts/validate_content.py`: Pydantic content schemas, a loader with an English overlay and hidden drafts, and a validator that runs every recipe and the Swedish spelling guard; `content/kompetenser.yaml`, `content/regler/bfl.yaml`, `content/dokumentmallar.yaml` and the sample lesson `m3.l2` (D3.1).
* `learning/recipes.py`: 24 recipes with seeded parameters and accepted alternative accounts, one hand calculated test each (D3.2).
* `learning/grading.py` and `learning/feedback.py` with `content/feedback.yaml`: eleven error codes and the five part feedback (D3.3).
* `learning/mastery.py`, `learning/gamification.py`, `learning/documents.py` and `services/practice.py` with `services/views.py`: skill states, repetition, XP, levels, svit and the practice use cases (D3.4).
* `learning/hitta_felet.py` and `learning/avstamning.py` (D3.5).
* `ui/components` (verifikation grid and table, document viewer, feedback panel, statement, hint) and the Övningar page (D3.6).

Changed after the day 3 review
* Owner checks for D2.2, D2.5, D2.6, D2.8 and D3.2 completed with sources; the hand calculated month now has expected figures and the engine agrees on every line. 2820 added to the kontoplan as an accepted account for utlägg; the momsbetalning recipe is now the skattekonto debitering (debet 2650, kredit 1630).
* Mastery: a success before the due date no longer moves the due date, so daily practice can reach Befäst.
* The smoke test now loads every page in both languages and checks that every interface string has an English text; CI also runs the content validator. Streamlit minimum raised to 1.60 for `width="stretch"` and right aligned grid columns.
* Engine: `vat.report` and `vat.settlement` take optional period bounds by date, so a second month's momsomföring no longer counts the first month's moms. `settlement` can book a net to get back on 1650 Momsfordran through `refund_account`; the default is still 2650. Approved by the owner in the day 3 review; one test for each.
* Recipes: `forsaljning_faktura` and `kreditfaktura` accept the dated `livsmedel` code, so exercises can show the 6 procent rate that applies from 1 April 2026.
