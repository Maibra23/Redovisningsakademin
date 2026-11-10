# PRD: Redovisningsakademin

**Version:** 0.3 (one week scope)
**Date:** 10 November 2026
**Owner:** Mustafa (GitHub: Maibra23)

Related documents: `docs/ARCHITECTURE.md`, `docs/TASKS.md` (the seven day plan), `CLAUDE.md`.

## 1. Product vision

Redovisningsakademin is a free, open, Swedish language training app for extern redovisning. A learner books real looking documents for a simulated Swedish aktiebolag, gets told exactly what was wrong and which rule applies, and sees proof of what they can do.

Value proposition in one sentence: **practise Swedish bookkeeping the way it is done at work, with the baskontoplan (BAS), moms and löner, and with feedback that teaches.**

The app has two audiences at once: learners, and employers who evaluate the owner's work. Both are served by the same qualities: correct accounting, clear Swedish, restrained design and honest limits.

## 2. Problem

Courses and textbooks explain theory but give few repetitions with feedback. Vendor guides teach where to click but assume you already know the entry. Quiz apps test recognition, not the ability to produce a verifikation from an invoice. No free resource without registration combines documents, booking, moms, löner, reports and rule references in one place.

## 3. Audience and access

* **Karriärbytaren (primary):** academic background, little hands on bookkeeping, applying for accounting roles. Includes the owner.
* **Nybörjaren:** no background, needs every term explained.
* **Den yrkesverksamma:** knows daily entries, wants to train moms, löner and månadsbokslut.

Access: anyone with the link uses everything. No login, no account, no personal data. Progress is saved under a random **sparkod** that lives in the page address, so a bookmark brings the learner back and the same link works on another device.

## 4. Language

* Swedish is the language of the interface and all learning content.
* Swedish must be correct and concise: full use of å, ä and ö, correct compounds (no särskrivning), consistent terminology from one glossary (`content/ordlista.yaml`), short sentences, the learner addressed as "du".
* The English term is shown once, in parentheses, when a concept is introduced. Example: verifikation (voucher).
* **English is an alternative language**, chosen with a switch. Interface, lessons, feedback and exams are translated. Account names, document contents and Swedish accounting terms stay in Swedish with the English explanation beside them, because the working language of Swedish bookkeeping is Swedish.
* Hyphens are used only where correct Swedish requires them (for example T-konto and BAS-kontoplanen); otherwise texts avoid dash characters.
* Detailed writing rules are in `CLAUDE.md` section 8.

## 5. Accounting standard

* The **baskontoplan (BAS)** is the chart of accounts for everything: lessons, exercises, simulator and reports. Account numbers and names are taken from the current official BAS publication at bas.se, never from memory.
* The app uses a subset of roughly 50 accounts, enough for the content of the week.
* Reference company form: small aktiebolag, K2, faktureringsmetoden, calendar year, moms reported monthly.
* Note on rights: BAS states in its terms that copyright stays with BAS. The app credits BAS as the source on the kontoplan page. The owner sends BAS a short question about educational use in parallel (task D7.4). This does not block the build.

## 6. Learning design

**Four questions.** Every lesson concept has four mandatory fields: Vad (what it is), Varför (its purpose), Hur (the procedure and the entry), När (when it applies and when it does not).

**Lesson loop.** Förklara (short text), Visa (one worked example with document, entry and effect on the reports), Gör (at least three exercises with new numbers each time), Kontroll (a short check without hints).

**Exercise types in the week.**
* Kontering: build a verifikation from a document. The core type.
* Beräkning: compute moms, avskrivning, nettolön, arbetsgivaravgifter.
* Klassificering: place items in kontoklass or in tillgång, skuld, eget kapital, intäkt, kostnad.
* Hitta felet: a booked verifikation contains one planted error; correct it.
* Avstämning: compare a kontoutdrag with the bank account in the huvudbok, find the differences and book what is missing.
* Resonemang: choose the correct justification and rule for an entry.

**Feedback in five parts** on every wrong answer: what was wrong, why, the correct treatment, the rule with its source, and a tip for next time. The grader recognises common errors (debet and kredit swapped, moms on the gross amount, wrong momskonto, cost booked as asset) and words the first two parts accordingly.

**Mastery is shown, not granted.** Per skill: Ej påbörjad, Övar, Kompetent, Befäst. Kompetent needs at least 5 graded attempts and at least 80 percent correct over the latest 8 without hints, including one kontering. Befäst needs two successful repetitions on later days. Reading a lesson gives nothing.

**Repetition.** Practised skills come back after 1, 3 and 7 days. The dashboard starts with "Dagens repetition".

## 7. Curriculum for the week

Six modules, 20 lessons, 19 skills.

**M1 Grunderna.** Vad extern redovisning är och vem som läser den; bokföringsekvationen; debet och kredit; baskontoplanen och kontoklasserna. Skills: A1 Bokföringsekvationen, A2 Debet och kredit, A3 Baskontoplanen.

**M2 Regler för bokföringen.** Bokföringsskyldighet och verifikationens innehåll; rättelser, arkivering och normhierarkin i korthet. Skills: A4 Verifikationen och löpande bokföring, B5 Rättelser.

**M3 Löpande bokföring.** Försäljning mot faktura och inbetalning; inköp mot faktura och utbetalning; bank, kort och utlägg; inventarier, förbrukningsinventarier och avskrivning. Skills: B1 Kundfakturor, B2 Leverantörsfakturor, B3 Bank, kort och utlägg, B4 Inventarier och avskrivningar.

**M4 Moms.** Grundprincipen och skattesatserna; moms i bokföringen; handel med EU och omvänd betalningsskyldighet (köp och försäljning av varor och tjänster mellan företag i olika EU länder); momsavstämning och momsredovisning. Skills: C1 Utgående och ingående moms, C2 Skattesatser, C3 Momsavstämning, C4 Moms vid handel med EU.

**M5 Löner.** Löneverifikationen: bruttolön, skatteavdrag, nettolön; arbetsgivaravgifter, skattekontot och arbetsgivardeklarationen i översikt. Skills: L1 Löneverifikationen, L2 Arbetsgivaravgifter och skattekonto.

**M6 Månadsbokslut och rapporter.** Bankavstämning; periodiseringar; råbalans och felsökning; att läsa resultaträkning och balansräkning. Skills: D1 Periodiseringar, D2 Råbalans och felsökning, D3 Bankavstämning, E1 Resultaträkning och balansräkning.

**Prov.** One exam per module (8 items) and one slutprov (20 items across all modules). No hints and no AI help during the exam, feedback after submission, pass mark 80 procent, result stored.

**Regelbibliotek.** About 18 rule entries that the lessons cite, from Bokföringslagen (1999:1078), Mervärdesskattelagen (2023:200), Årsredovisningslagen (1995:1554), Bokföringsnämnden and Skatteverket. Each entry has the name, chapter and section, a plain explanation, an example, the type of norm, an official source link and the date it was checked.

**Role view.** The competency profile groups the 19 skills under two targets: Ekonomiassistent (A1 to A4, B1 to B3, C1, C2, D3) and Redovisningsassistent (all 19).

## 8. Simulator

The learner is the accountant of **Nordvik Kontorsmiljö AB**, a fictional company selling office furniture and ergonomics services, with three employees.

* **Inkorg:** about 22 documents for one month in date order: kundfakturor, leverantörsfakturor, kvitton, bankhändelser, a lönespecifikation, a hyresavi, one purchase from and one sale to a company in another EU country.
* **Bokför:** the learner builds the verifikation. An unbalanced entry is refused with an explanation, as in real systems.
* **Rättelse:** a booked verifikation cannot be edited. It is corrected with a new verifikation that refers to the old one. The app teaches the lawful method through its own mechanics.
* **Rapporter:** verifikationslista, huvudbok, råbalans, resultaträkning, balansräkning and momsrapport, always computed from the learner's own entries.
* **Bankavstämning:** the month's kontoutdrag is compared with the bank account in the huvudbok. Two differences are planted; the learner finds them and books what is missing.
* **Månadens avslut:** the last missions are löner with arbetsgivaravgifter, avskrivning, a förutbetald kostnad, and momsavstämning with omföring to the momsredovisningskonto.
* Every document is checked on submit with the five part feedback. The learner can reset and start again; numbers change with each new start.

## 9. Gamification

Points follow demonstrated skill only.

* **XP** per graded attempt by difficulty (Grund 10, Medel 20, Avancerad 35): full on a correct first attempt without hints, half otherwise, none after the solution is shown.
* **Nivåer:** Praktikant, Bokföringsbiträde, Ekonomiassistent, Redovisningsassistent, Redovisningsekonom. The levels Ekonomiassistent and Redovisningsassistent also require the skills of the matching role target at Kompetent.
* **Svit:** days in a row with at least one graded activity.
* **Märken:** seven badges for competence events, for example "Första balanserade verifikationen", "Momsen stämmer", "Lönen är bokförd", "Banken är avstämd", "Månaden avslutad", "Godkänt slutprov".
* **Dagens utmaning:** five mixed items chosen from the date, the same for everyone.

## 10. AI layer (Qwen through Hugging Face)

**Assessment.** Including a language model is a good idea for two jobs and a bad idea for two others.

* **Good: new scenarios.** The model writes the story around an exercise (company, counterparty, goods, situation) so that practice never repeats. All amounts, accounts and the answer key still come from the accounting engine.
* **Good: live explanation.** After the grader has decided, the model can explain the mistake in other words and answer follow up questions about the current exercise, using only the facts it is given.
* **Bad: grading.** A model can be confidently wrong. The deterministic grader alone decides right and wrong.
* **Bad: writing rules or keys.** The model never states a law, a rate or an account that the app did not supply.

**Why it is worth it.** It gives unlimited variety, a tutor like experience, and it shows an employer responsible AI engineering: grounding checks, fallbacks and cost limits. The owner's existing ekonomistyrning app already has a tested client, prompt library, text cleaner and call budget for Qwen that are reused here.

**Risks and how they are handled.**
* Swedish quality of Qwen is uneven. Core lesson text is therefore never model written. Model text is short, cleaned, checked and labelled "Förklaring skapad av AI".
* Wrong numbers. Every amount and account number in the model's answer must exist in the facts sent to it; otherwise the answer is discarded and the built in explanation is shown.
* Cost and abuse on an open app. A cap per session and a cap per day for the whole app.
* Outage or no token. Everything works without the model; the buttons are hidden.

**Features.** "Förklara med andra ord" on feedback; "Fråga handledaren" about the current exercise; "Nytt scenario" in practice and in the simulator.

## 11. Navigation

* **Hem:** Översikt.
* **Lär:** Lektioner; Övningar; Repetition; Prov.
* **Praktik:** Bokföringssimulatorn; Regelbibliotek; Kontoplan.
* **Min utveckling:** Kompetensprofil; Prestationer; Inställningar.

Design: one main action per screen; verifikationer always in the same table with konto, kontonamn, debet and kredit; amounts right aligned in Swedish format; colour for meaning only; no decorative animation. The visual identity reuses the design system of the owner's ekonomistyrning app.

## 12. Requirements and acceptance criteria

* **R1 Access.** A new visitor reaches a first exercise in two clicks. Reopening the bookmarked address restores progress.
* **R2 Lessons.** Every lesson has the four fields, a worked example, at least three exercises and a check.
* **R3 Grading.** Kontering accepts any row order and declared alternative accounts. Wrong answers show the five parts.
* **R4 Engine.** Unbalanced entries are refused. Reports derive only from booked entries. Tillgångar equal eget kapital plus skulder after every entry. Rates are data with dates.
* **R5 Simulator.** The full month can be completed; corrections create linked verifikationer; reports update at once.
* **R6 Mastery and profile.** States change only through graded attempts. The profile shows state, accuracy and attempts per skill and progress toward both role targets.
* **R7 Regelbibliotek.** Every entry has a source and a checked date. Every rule cited in a lesson exists in the library.
* **R8 AI layer.** No model output is shown that failed the grounding check. The app is fully usable with the model off.
* **R9 Swedish.** No learner facing text without å, ä, ö where they belong; all terms match the glossary.
* **R11 Exams.** A module exam and the slutprov can be taken; no help is available before submission; the result is stored and shown in the profile.
* **R12 English.** With English chosen, no interface string is untranslated and every lesson has an English version.
* **R10 Notice.** Pages with legal or tax content state that the material is educational and not professional advice.

## 13. Quality requirements

Exact money (integer öre). Engine independent of Streamlit and of the database. Content as data files. A small, focused test set on the engine (see `CLAUDE.md` section 10). Responses within about one second after warm start. No personal data and no trackers.

## 14. What an employer should see

* A live app that works on first click.
* A README with screenshots, the architecture diagram and a short method section.
* Correct, verifiable accounting with sources.
* An honest `docs/LIMITATIONS.md`.
* A clean repository history with small commits per task and a green CI badge.

## 15. After the week (roadmap)

Import and export outside the EU; omvänd betalningsskyldighet for byggtjänster; kundreskontra and leverantörsreskontra; kassaflödesanalys and nyckeltal; a diagnostic test; a second company with bokslutsmetoden; SIE export.

## 16. Risks

* **Incorrect content.** Keys computed by the engine, sources on every rule, owner review on day 7, a visible "Rapportera fel" link.
* **One week is tight.** The plan fixes the scope in section 7 and moves everything else to the roadmap. With EU moms, bankavstämning, prov and English included the week is full. If a day slips, the cut order is: Dagens utmaning, Nytt scenario in the simulator, Hitta felet, English lesson text (the English interface stays).
* **Rule changes.** Example: moms on livsmedel is 6 percent instead of 12 percent from 1 April 2026 through 31 December 2027. Rates are dated data.
* **Free hosting.** The app sleeps when idle and local files are not kept, so progress is stored in an external PostgreSQL database.
* **Sparkod in the address.** Anyone who gets the link can open that progress. Accepted, since it holds no personal data; the settings page says so.
