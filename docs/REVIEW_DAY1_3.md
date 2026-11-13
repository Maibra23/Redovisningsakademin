# Review after days 1 to 3

**Date:** 13 November 2026
**Scope:** everything built in D1.1 to D3.6, checked against `docs/PRD.md`, `docs/ARCHITECTURE.md`, `CLAUDE.md` and the task prompts in `docs/TASKS.md`.
**Purpose:** confirm the three days are complete, list every limitation, issue and gap found, and give a concrete, implementable fix for each. Items are ranked by how much they threaten the week's goal (a correct, honest, working app that an employer can read).

## 1. Status of days 1 to 3

All 19 tasks are ticked in `docs/TASKS.md` with a result line. The three checks run clean on commit `938f694`:

| Check | Result |
|---|---|
| `pytest` | 49 passed |
| `ruff check .` | all checks passed |
| `python scripts/validate_content.py` | OK: 1 lesson, 5 exercises, 1 rule, 24 recipes, 0 problems |

Verified beyond the automated checks: the Övningar page was driven in a headless Chromium session; a leverantörsfaktura booked correctly gave "Rätt svar" and 20 XP, and the same exercise booked with debet and kredit swapped gave the five part feedback for `FEL_SIDA`. The mastery demo moved skill B2 from Ej påbörjad to Övar to Kompetent on the fifth graded attempt.

Six Day 3 commits are on local `main` and are **not yet pushed** to GitHub, so CI has not run on them.

### Owner steps that are still open

These are marked **(Ägare)** in the task list and only you can do them:

| Task | What is waiting |
|---|---|
| D2.2 | Spot check ten accounts and the classification columns (kind, normal side, report line, moms role) in `content/kontoplan.yaml`. BAS gives only number and name; the rest is the app's own classification. |
| D2.5 | Approve the four EU treatments, especially 2614 for utgående moms on EU purchases (2615 is for import) and 4535 under Råvaror och förnödenheter. |
| D2.6 | Confirm the three verifikation approach for payroll and the rounding of avskrivningar. |
| D2.8 | Hand calculate råbalans, resultat and balans for `tests/hand_calculated_month.md` and give the figures to Claude. Until then `test_hand_calculated_month_reports_run` checks only the engine's own invariants, not the figures. |
| D3.2 | Review the recipe table (accounts and alternatives) against a textbook. The table is in the reply to D3.2; the figures are in `tests/test_recipes.py`. |
| D3.2 | Decide the open account questions: 2820 for utlägg, one or two step momsbetalning, hyra with or without moms. |

## 2. Findings that affect correctness

### 2.1 Spaced repetition can never reach Befäst for a learner who practises daily

**Where:** `src/ra/learning/mastery.py`, `update` and `next_due`.
**Problem:** after a success that is not due, the due date is recomputed from today, so practising every day pushes the due date ahead by three days each time and the second repetition is never "due". Befäst then becomes unreachable for the most active learners, the opposite of the intent in PRD section 6.
**Fix (30 min):** keep `due_on` unchanged on a success that is not yet due; move it only on a due success (to the next interval) or on a miss (back to one day). In `update`, replace the unconditional `due_on=next_due(...)` with: if not success, `next_due(today, False, 0)`; elif was_due, `next_due(today, True, repetitions)`; else `progress.due_on`. Add one test in `test_recipes.py` or a small `test_learning.py` (allowed by CLAUDE.md section 10 as "one test that would have caught it"): seven daily successes starting from Ej påbörjad must reach Befäst on the day the second repetition is due.

### 2.2 Moms report and momsomföring are correct for one period only

**Where:** `src/ra/core/vat.py`, `_period_vouchers`.
**Problem:** the report sums every verifikation in the journal except those touching 2650. After the first momsomföring the next period's report counts the earlier months' sales and purchases again, so a second settlement double counts. The simulator (D5) is one month, so the week is safe, but the architecture promises "rates by date" and a month closing flow; a second month or any multi period exam would be wrong.
**Fix (1 h, engine change, needs your approval and a CHANGELOG note per CLAUDE.md rule 1):** give `report` and `settlement` optional `period_from` and `period_to` dates and sum only verifikationer dated inside the period. Keep the current behaviour when no period is given. One test: two months booked, settlement for month two equals month two's moms only.

### 2.3 A moms refund is left on 2650 instead of 1650 Momsfordran

**Where:** `src/ra/core/vat.py`, `settlement`; `content/kontoplan.yaml` already has 1650.
**Problem:** when ingående moms exceeds utgående, the net goes to debet 2650. That is acceptable during the year, but at a bokslut practice moves a fordran to 1650, and lesson M4.4 will need to say which. Right now the engine cannot produce the 1650 treatment.
**Fix (45 min, engine change):** add a `refund_account` parameter to `settlement` (default `None` keeps 2650); when set and the net is negative, book the net on debet 1650. Mark both as accepted in the momsomföring recipe (`alternatives={2650: {1650}}` for a negative net) and say so in the feedback, as CLAUDE.md section 7 asks when two treatments are acceptable.

### 2.4 The dated rate feature is never exercised

**Where:** `src/ra/learning/recipes.py`; `content/momssatser.yaml`.
**Problem:** the engine supports the temporary 6 procent on livsmedel, but no recipe uses the `livsmedel` code, so no exercise can show a rate that depends on the date. Skill C2 Skattesatser (lesson M4.1) has no recipe to demonstrate the main thing the PRD calls out as a risk.
**Fix (45 min):** add `momskod: ["moms_25", "moms_12", "moms_6", "livsmedel"]` support in `_sale` by mapping the resolved rate to the 3001 to 3003 and 2611 to 2631 accounts (already done by rate, so only the option list and the description "Livsmedel till personalrestaurang" are needed). Add one hand calculated test with a date before and after 1 April 2026. The grader already classifies a wrong rate as `MOMS_FEL_SATS`.

### 2.5 XP can be farmed on one easy exercise

**Where:** `src/ra/services/practice.py`, `submit`; `src/ra/learning/gamification.py`.
**Problem:** "Ny uppgift" creates a new seed, and a new seed is a new instance, so a learner can earn full XP indefinitely from the same grund exercise. Mastery is protected (the latest eight window and the kontering requirement), but levels and the svit are not, and PRD section 9 says "points follow demonstrated skill only".
**Fix (1 h):** in `submit`, count the learner's correct attempts on the same `item_id` today; award full XP for the first two, half for the third and fourth, none after that. Put the rule in `gamification.xp_for` as a `correct_today` argument so it stays a pure function, and show the reason in the caption ("Fler försök på samma övning i dag ger ingen XP"). Needs one query in `storage/queries.py`.

## 3. Gaps against the architecture and the PRD

### 3.1 The smoke test is a placeholder and CI does not run the content validator

**Where:** `tests/test_smoke.py`, `.github/workflows/ci.yml`.
**Problem:** architecture section 11 promises a smoke test that starts the app, loads every page in both languages and checks that every interface string has an English text. The current file only imports `ra`. CI runs ruff and pytest but not `scripts/validate_content.py`, so a broken lesson file can reach `main` with a green badge.
**Fix (1 h):** write `test_smoke.py` with `streamlit.testing.v1.AppTest.from_file("app.py")`, loop over the page paths from `navigation.PLACEHOLDERS` plus `oversikt` and `om-appen`, set `session_state["lang"]` to `sv` and `en`, run, and assert `not at.exception`. For the string check, walk `src/ra/ui` with `ast`, collect every literal first argument to `t()` (the script used during D3.6 does exactly this), and assert each is a key in `texts_en.EN`. Point `DATABASE_URL` at a temporary SQLite file through `monkeypatch`. Add `python scripts/validate_content.py` as a CI step after pytest.

### 3.2 No README

**Where:** repository root.
**Problem:** PRD section 14 lists a README with screenshots, the architecture diagram and a method section as what an employer should see first. It is planned for D7.5, but the repository is already public and the Day 3 screenshots exist in the scratch folder only.
**Fix (now, 20 min; polish in D7.5):** add a short README with the one sentence value proposition, the stack, the three commands, the link to the live app and the CI badge. Save the two Day 3 screenshots (right and wrong answer) under `docs/img/` for D7.5.

### 3.3 Day 3 is missing from the changelog

**Where:** `CHANGELOG.md`.
**Problem:** Days 1 and 2 are recorded; Day 3 is not. There was no engine change, so CLAUDE.md rule 1 did not force an entry, but the file is part of the portfolio and should stay complete.
**Fix (10 min):** add a "Day 3: learning engine and exercise interface" section listing the six tasks, in the same style as Day 2.

### 3.4 English mode has no content and the loader's overlay is untested

**Where:** `content/en/` (empty), `src/ra/learning/loader.py`.
**Problem:** the loader serves `content/en/<same path>` when English is chosen, but no English file exists, so the code path has never run. D7.3 adds the texts; a wrong relative path convention would surface only then.
**Fix (20 min, now):** add one English copy of the sample lesson under `content/en/moduler/m3/l2.yaml` with only the four fields and the titel translated, and let `validate_content.py` check that every English file has the same ids and the same exercise ids as its Swedish source (a loop over `read_content(root, "en")` comparing `lessons[id].ovningar` ids). This also decides the convention early: English files translate text only; `recept`, `parametrar`, `regel` and ids are copied unchanged.

### 3.5 Streak and attempt storage live in the practice service only

**Where:** `src/ra/services/practice.py`, `_update_streak`.
**Problem:** the simulator (D5), prov (D6.4) and Dagens utmaning (D6.6) must also store attempts and count toward the svit. If each service reimplements the write, they will drift.
**Fix (30 min, before D5):** move `_update_streak` and the attempt write into `src/ra/services/progress.py` as `record_attempt(session, learner_id, attempt_values, on_date)` and call it from practice now and from the simulator and exam services later. No behaviour change.

### 3.6 Keep warm pings may not keep the database awake

**Where:** `.github/workflows/keep_warm.yml`.
**Problem:** the workflow fetches the app's index page with curl. A plain HTTP GET returns the static shell without running `app.py`, so the database is not touched; Supabase pauses free projects after seven days without activity, and whether Streamlit Community Cloud counts a GET as traffic is undocumented.
**Fix (20 min):** Streamlit 1.67 exposes an agent endpoint on the app (`POST <app>/_stcore/agent/interact` with body `{}`), which starts a real session and runs the script, including `learner.get_or_create`, so the database is used. Replace the curl line with `curl -X POST -H "Content-Type: application/json" -d '{}' "$APP_URL/_stcore/agent/interact"`. If the endpoint is disabled on Community Cloud, add a second job that runs `python -c "import psycopg, os; psycopg.connect(os.environ['DATABASE_URL']).execute('select 1')"` with the database address as a repository secret.

### 3.7 PostgreSQL has not been exercised

**Where:** `src/ra/storage/db.py`; `docs/LIMITATIONS.md` already notes it.
**Problem:** every run so far used SQLite. The Supabase pooler settings (`prepare_threshold=None`, pool size 2) and the JSON columns are untested on PostgreSQL; the first production visitor would find out.
**Fix (30 min, owner):** create the Supabase project, put `DATABASE_URL` in `.streamlit/secrets.toml` locally, run the app once, do one exercise, and confirm rows in `learner`, `attempt` and `skill_state` in the Supabase table editor. Then deploy.

## 4. Interface and usability

### 4.1 Empty account cells show "None"

**Where:** `src/ra/ui/components/voucher.py`.
**Problem:** Streamlit's selectbox column shows a grey "None" placeholder in empty cells. It is not learner text and cannot be changed in Streamlit 1.67.
**Fix (15 min):** start the grid with one empty row instead of four (`EMPTY_ROWS = 1`) and rely on `num_rows="dynamic"`; one "None" is far less confusing than four. Add a one line caption under the grid: "Välj konto, skriv beloppet och tryck Enter."

### 4.2 The grid needs a keyboard pattern that is not obvious

**Problem:** a cell is edited by selecting it and pressing Enter, then typing. First time users will click and type, which does nothing.
**Fix (10 min):** the same caption as 4.1, translated. For D7.4, consider a fallback form for phones: three `st.selectbox` and `st.text_input` rows inside an expander, since `st.data_editor` is hard to use on a touch screen.

### 4.3 Feedback for a right answer after a wrong one is ambiguous

**Problem:** the second attempt on the same instance is graded but gives no XP and does not count. The caption says so, but the learner may not notice that "Rätta svaret" on a corrected grid is attempt two.
**Fix (10 min):** after the first result, relabel the primary button "Rätta igen (räknas inte)" and make "Ny uppgift" the primary button.

### 4.4 Hint state grows per instance in session state

**Where:** `src/ra/ui/components/hint.py`.
**Problem:** a key `tips_<exercise>_<seed>_visad` is left in session state for every instance ever shown in the session. Harmless for a session, but untidy.
**Fix (10 min):** clear keys starting with `tips_` in `_new_exercise` in `ovningar.py`.

## 5. Content and language risks for day 4

### 5.1 Day 4 is the largest day and the validator is strict by design

**Problem:** 20 lessons, about 60 exercises, 18 rule entries and 90 glossary terms in one day, every rule checked at the source. The spelling guard and the dash rule reject files on a single slip.
**Fix:** write and validate one module at a time, commit each; keep every rule entry `utkast` until its source was opened in the same session (the validator already refuses a published lesson that cites an utkast rule). Reuse the sample lesson `m3.l2` as the template. If the day slips, PRD section 16 allows cutting Hitta felet content (the exercise type stays).

### 5.2 Hitta felet and Avstämning have no content yet

**Problem:** both types are graded by the service and tested, but no lesson uses them, so they have never been shown on the page.
**Fix (20 min, early in D4.6):** add one `hitta_felet` exercise to M2.2 (Rättelser, skill B5) and one `avstamning` exercise to M6.1 (skill D3), run the page once with drafts shown, and fix any layout issue before writing the rest of M6.

### 5.3 The glossary is referenced but does not exist

**Where:** `content/ordlista.yaml` (D4.1), `CLAUDE.md` section 8.
**Problem:** the term rule ("use the term in ordlista.yaml and no synonym") cannot be checked until the glossary exists, and the LLM prompts (D6.1) include it.
**Fix:** D4.1 writes it; then extend the validator with a soft check that warns (does not fail) when a lesson uses a listed synonym such as "verifikat" for "verifikation" or "ingående skatt" for "ingående moms". A small `synonymer` list per term in the glossary file is enough.

## 6. Smaller code observations

| Where | Observation | Suggested change |
|---|---|---|
| `learning/recipes.py` (561 lines) | Largest file; still under the 800 limit but D4 and D5 may add recipes. | Split into `recipes/` package: `registry.py`, `sales.py`, `purchases.py`, `payroll.py`, `vat.py`, `eu.py`. No behaviour change. |
| `services/practice.py` (398 lines) | Holds content access, grading dispatch and persistence. | Move `library`, `account_options`, `available_skills` to `services/content.py`; the simulator and lesson pages will need them too. |
| `learning/hitta_felet.py` and `grading.py` | `_other(side)` is defined in both. | One helper in `core/voucher.py` (`Side.other`). |
| `learning/grading.py`, `classify` | Pairing of leftover rows is greedy; with two wrong accounts on the same side the pairing may name the less likely one. | Acceptable; the first code is still right. Revisit only if feedback looks odd in D7.1. |
| `ui/pages/ovningar.py` | `PROBLEM_TEXTS` and `DEFAULT_INSTRUCTIONS` are Swedish strings in code, translated through `t()` at use. | Fine; keep the pattern. |
| `content/kompetenser.yaml` | Written in D3.1 because the validator needs it; D4.1 also lists it. | Treat D4.1 as a review of the file, not a rewrite. |
| `pyproject.toml` | `streamlit>=1.50`, but the code uses `width="stretch"` and `alignment="right"`, which need a newer Streamlit than 1.50. | Raise to `streamlit>=1.60` (the local version is 1.67) so Community Cloud and CI cannot resolve an older release. |

## 7. Security and privacy check

Checked against CLAUDE.md rules 8 and 9 and the global security checklist:

* No secrets in the repository; `.streamlit/secrets.toml` is ignored and only the example is committed.
* All SQL goes through SQLAlchemy; no string built queries.
* Every HTML fragment in `ui/components` and `ui/theme.py` passes learner and content text through `html.escape`; the rule link uses `escape(quote=True)` and `rel="noopener noreferrer"`.
* No personal data is stored; the sparkod is stored as a SHA 256 hash.
* No copied text: lesson, feedback and template texts are original; account names are copied from BAS by script, which BAS permits with credit (the Kontoplan page in D4.7 must carry the credit).
* Open item: the simulator (D5) will accept free verifikation text from the learner; limit it to 200 characters (the `SimVoucher.text` column already does) and show it only as plain text.

## 8. Recommended order

Do these before starting D4.1; together they take about half a day and remove the correctness risks while the code is fresh:

1. Push the six Day 3 commits and confirm CI is green.
2. Fix 2.1 (repetition due date) with its one test.
3. Write the smoke test and add the validator to CI (3.1).
4. Raise the Streamlit minimum (section 6) and add the Day 3 changelog entry (3.3).
5. Add the README skeleton (3.2).
6. Give Claude the hand calculated month figures (D2.8) and the answers to the D3.2 account questions, so the engine and recipes are confirmed before 20 lessons are written on top of them.

Schedule 2.2, 2.3 and 2.4 for the start of D4.4 (Moms), since that module is where they become visible, and 3.5 for the start of D5.2. The rest can wait for D7.2 and D7.4.
