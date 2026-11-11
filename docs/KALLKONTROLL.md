# Källkontroll: log of checked sources

Every law, rate, threshold and BAS account used in the app is checked against the
official source in the task that introduces it. One row per check, newest last.

| Date | What | Where | Result |
|---|---|---|---|
| 2026-11-11 | BAS-kontoplanen: numbers and names for the 58 accounts in `content/kontoplan.yaml` (D2.2) | Official publication "Kontoplan BAS 2026", file `BAS_kontoplan_2026_v2.xlsx` (sheet version v 1.1), linked from https://www.bas.se/kontoplaner/ ; direct file https://www.bas.se/wp-content/uploads/2026/04/BAS_kontoplan_2026_v2.xlsx ; SHA 256 a86b39937fab280d4e5db895c04c2af6e145695863d4845ff14eea5d0302328a | All 58 numbers exist; names copied from the file by script; none of them is marked # (not for K2). Found while checking: 4515 is "råvaror och material", so EU purchases of trade goods use 4075; account 4598 does not exist in BAS 2026. Kind, normal side, report line and moms role are the app's classification, not part of the BAS file; owner to review. |
