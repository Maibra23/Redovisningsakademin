# Redovisningsakademin

[![CI](https://github.com/Maibra23/Redovisningsakademin/actions/workflows/ci.yml/badge.svg)](https://github.com/Maibra23/Redovisningsakademin/actions/workflows/ci.yml)

A free, open Swedish language training app for extern redovisning. You book realistic documents for a simulated aktiebolag with BAS-kontoplanen, and the app tells you exactly what was wrong, why, and which rule applies.

**Practise Swedish bookkeeping the way it is done at work, with BAS, moms and löner, and with feedback that teaches.**

The app is built in one week; this README grows with it. The plan is in `docs/TASKS.md`, the product in `docs/PRD.md` and the design in `docs/ARCHITECTURE.md`.

## How it works

* A pure Python accounting engine (`src/ra/core`) with integer öre, an append only journal, moms by date, payroll, depreciation, bank reconciliation and reports. Every figure a learner sees comes from it.
* Exercises are recipes: sampled parameters in, document figures and the answer key out, so every attempt has new numbers and the key always agrees with the engine.
* A deterministic grader classifies mistakes (debet and kredit swapped, moms on the gross, wrong momskonto, and more) and builds feedback in five parts with the rule and its official source.
* Mastery is shown, not granted: skill states change only through graded attempts, with spaced repetition after 1, 3 and 7 days.
* No login and no personal data: progress lives under a random sparkod in the page address.

## Run it

```
pip install .[dev]
streamlit run app.py
pytest
ruff check .
python scripts/validate_content.py
```

Without `DATABASE_URL` the app uses a local SQLite file. Content with status utkast is shown only with `RA_SHOW_DRAFTS=1`.

## Stack

Python 3.12, Streamlit, SQLAlchemy 2 with PostgreSQL (Supabase) in production, Pydantic 2, YAML content, pytest and ruff.

## Sources and limits

Account numbers and names come from the official BAS 2026 kontoplan (copyright BAS). Every rate, law and account used is logged in `docs/KALLKONTROLL.md` with the date it was checked. Known gaps are listed honestly in `docs/LIMITATIONS.md`. The material is educational and not professional advice.

## Licence

MIT, see `LICENSE`.
