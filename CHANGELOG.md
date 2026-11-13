# Changelog

Notable changes, newest first. Version 1.0 is written at the end of the week (D7);
until then entries collect under "Unreleased", grouped by task.

## Unreleased

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
