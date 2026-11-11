# Limitations

Known gaps and simplifications. The full version is written in task D7; until then
every gap found during the build is added here.

* **Sparkod in the address.** Anyone who gets the link can open that progress. Accepted because no personal data is stored; the "Om appen och integritet" page says so.
* **PostgreSQL not yet verified end to end.** Storage and the learner flow were verified locally on SQLite. The check against Supabase PostgreSQL is the owner's deployment step after D1.5.
* **Settings actions not yet in the interface.** "Om appen och integritet" mentions resetting and deleting progress under Inställningar. The service functions exist (D1.4); the page is still a placeholder.
* **Moms rate date.** The legal rule uses the date of the beskattningsgrundande händelse; the engine uses the date of the transaction given to it. For the exercises these are the same date.
* **Momsomföring in öre.** `vat.settlement` moves the exact amount in öre to 2650. Rounding the momsdeklaration to whole kronor with öresutjämning on 3740 is not modelled.
* **Moms report period.** `vat.report` treats the whole journal as the period and leaves out verifikationer that touch the momsredovisningskonto (earlier omföringar). Periods within a journal are not yet supported.
* **EU trade.** Only purchases and sales between businesses under the huvudregel, at 25 procent, are modelled. Trepartshandel, kedjetransaktioner, sales to private persons (OSS), the periodisk sammanställning and the 12 and 6 procent rates on EU purchases are not.
* **Payroll.** Skatteavdrag is an input; tax tables are not modelled. Only the full arbetsgivaravgift is used; age based reductions and växa-stöd are not. Avgifter are computed in öre on the summed bruttolön, while the arbetsgivardeklaration works in whole kronor. The payment voucher moves money from the bank to the skattekonto (1630); the debitering of 2710 and 2731 against 1630 is a separate verifikation.
* **Depreciation.** Straight line per month only, with each month rounded down to whole öre and the remainder in the last month. Residual value, half year conventions and degressive plans are not modelled.
