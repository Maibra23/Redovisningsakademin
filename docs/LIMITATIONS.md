# Limitations

Known gaps and simplifications. The full version is written in task D7; until then
every gap found during the build is added here.

* **Sparkod in the address.** Anyone who gets the link can open that progress. Accepted because no personal data is stored; the "Om appen och integritet" page says so.
* **PostgreSQL not yet verified end to end.** Storage and the learner flow were verified locally on SQLite. The check against Supabase PostgreSQL is the owner's deployment step after D1.5.
* **Settings actions not yet in the interface.** "Om appen och integritet" mentions resetting and deleting progress under Inställningar. The service functions exist (D1.4); the page is still a placeholder.
