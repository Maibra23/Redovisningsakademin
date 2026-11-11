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
