# Hand calculated month (D2.8)

A small aktiebolag (K2, faktureringsmetoden, calendar year, moms reported monthly) in June 2026.
Amounts are in whole kronor. The engine runs the same verifikationer in `tests/test_core.py`
(`HAND_MONTH_OPENING` and `HAND_MONTH`).

**For the owner:** calculate the råbalans, the resultaträkning and the balansräkning by hand
or in a spreadsheet and fill in the empty tables at the end. Claude then encodes your figures
as the expected values and reports every difference from the engine without changing either side.

## Verifikationer

| Nr | Datum | Text | Konto | Kontonamn | Debet | Kredit |
|---|---|---|---|---|---:|---:|
| IB | 2026-06-01 | Ingående balans | | | | |
| | | | 1220 | Inventarier, verktyg och installationer | 60 000 |  |
| | | | 1229 | Ackumulerade avskrivningar på inventarier, verktyg och installationer |  | 12 000 |
| | | | 1460 | Lager av handelsvaror | 40 000 |  |
| | | | 1510 | Kundfordringar | 25 000 |  |
| | | | 1930 | Företagskonto | 180 000 |  |
| | | | 2081 | Aktiekapital |  | 25 000 |
| | | | 2091 | Balanserad vinst eller förlust |  | 138 000 |
| | | | 2350 | Andra långfristiga skulder till kreditinstitut |  | 100 000 |
| | | | 2440 | Leverantörsskulder |  | 18 000 |
| | | | 2650 | Redovisningskonto för moms |  | 12 000 |
| A1 | 2026-06-02 | Lokalhyra juni | 5010 | Lokalhyra | 12 000 |  |
| | | | 1930 | Företagskonto |  | 12 000 |
| A2 | 2026-06-03 | Kundfaktura 1001 | 1510 | Kundfordringar | 50 000 |  |
| | | | 3001 | Försäljning inom Sverige, 25 % moms |  | 40 000 |
| | | | 2611 | Utgående moms på försäljning inom Sverige, 25 % |  | 10 000 |
| A3 | 2026-06-05 | Leverantörsfaktura varor | 4010 | Inköp av handelsvaror i Sverige | 24 000 |  |
| | | | 2641 | Debiterad ingående moms | 6 000 |  |
| | | | 2440 | Leverantörsskulder |  | 30 000 |
| A4 | 2026-06-08 | Inbetalning kundfordran | 1930 | Företagskonto | 25 000 |  |
| | | | 1510 | Kundfordringar |  | 25 000 |
| A5 | 2026-06-10 | Betalning leverantörsskuld | 2440 | Leverantörsskulder | 18 000 |  |
| | | | 1930 | Företagskonto |  | 18 000 |
| A6 | 2026-06-12 | Betalning moms maj | 2650 | Redovisningskonto för moms | 12 000 |  |
| | | | 1930 | Företagskonto |  | 12 000 |
| A7 | 2026-06-15 | Inköp varor från Tyskland | 4075 | Inköp av handelsvaror från annat EU-land, 25 % moms | 20 000 |  |
| | | | 2645 | Beräknad ingående moms på förvärv från utlandet | 5 000 |  |
| | | | 2614 | Utgående moms omvänd betalskyldighet, 25 % |  | 5 000 |
| | | | 2440 | Leverantörsskulder |  | 20 000 |
| A8 | 2026-06-18 | Kortförsäljning | 1930 | Företagskonto | 6 250 |  |
| | | | 3001 | Försäljning inom Sverige, 25 % moms |  | 5 000 |
| | | | 2611 | Utgående moms på försäljning inom Sverige, 25 % |  | 1 250 |
| A9 | 2026-06-20 | Mobiltelefon juni | 6212 | Mobiltelefon | 800 |  |
| | | | 2641 | Debiterad ingående moms | 200 |  |
| | | | 1930 | Företagskonto |  | 1 000 |
| A10 | 2026-06-25 | Löneutbetalning juni | 7210 | Löner till tjänstemän | 35 000 |  |
| | | | 2710 | Personalskatt |  | 8 400 |
| | | | 1930 | Företagskonto |  | 26 600 |
| A11 | 2026-06-25 | Arbetsgivaravgifter juni | 7510 | Arbetsgivaravgifter 31,42 % | 10 997 |  |
| | | | 2731 | Avräkning lagstadgade sociala avgifter |  | 10 997 |
| A12 | 2026-06-28 | Bankavgift | 6570 | Bankkostnader | 150 |  |
| | | | 1930 | Företagskonto |  | 150 |
| A13 | 2026-06-30 | Avskrivning inventarier | 7832 | Avskrivningar på inventarier, verktyg och installationer | 1 000 |  |
| | | | 1229 | Ackumulerade avskrivningar på inventarier, verktyg och installationer |  | 1 000 |
| A14 | 2026-06-30 | Momsomföring juni | 2611 | Utgående moms på försäljning inom Sverige, 25 % | 11 250 |  |
| | | | 2614 | Utgående moms omvänd betalskyldighet, 25 % | 5 000 |  |
| | | | 2641 | Debiterad ingående moms |  | 6 200 |
| | | | 2645 | Beräknad ingående moms på förvärv från utlandet |  | 5 000 |
| | | | 2650 | Redovisningskonto för moms |  | 5 050 |

Notes:
* The ingående balans is the opening balance of the journal, not a verifikation of its own, so the month has the IB and 14 verifikationer (A1 to A14), 15 items in all.
* Arbetsgivaravgifter in A11: 35 000 x 31,42 % = 10 997,00 kr.
* A6 pays last month's moms, booked on 2650 in the ingående balans.
* A7 is an EU purchase of goods with omvänd betalningsskyldighet: calculated moms 20 000 x 25 % = 5 000 on 2614 and 2645.
* A14 moves the month's moms to 2650.

## Expected råbalans (owner fills in)

| Konto | Kontonamn | Utgående balans debet | Utgående balans kredit |
|---|---|---:|---:|
| 1220 | Inventarier, verktyg och installationer | | |
| 1229 | Ackumulerade avskrivningar på inventarier, verktyg och installationer | | |
| 1460 | Lager av handelsvaror | | |
| 1510 | Kundfordringar | | |
| 1930 | Företagskonto | | |
| 2081 | Aktiekapital | | |
| 2091 | Balanserad vinst eller förlust | | |
| 2350 | Andra långfristiga skulder till kreditinstitut | | |
| 2440 | Leverantörsskulder | | |
| 2611 | Utgående moms på försäljning inom Sverige, 25 % | | |
| 2614 | Utgående moms omvänd betalskyldighet, 25 % | | |
| 2641 | Debiterad ingående moms | | |
| 2645 | Beräknad ingående moms på förvärv från utlandet | | |
| 2650 | Redovisningskonto för moms | | |
| 2710 | Personalskatt | | |
| 2731 | Avräkning lagstadgade sociala avgifter | | |
| 3001 | Försäljning inom Sverige, 25 % moms | | |
| 4010 | Inköp av handelsvaror i Sverige | | |
| 4075 | Inköp av handelsvaror från annat EU-land, 25 % moms | | |
| 5010 | Lokalhyra | | |
| 6212 | Mobiltelefon | | |
| 6570 | Bankkostnader | | |
| 7210 | Löner till tjänstemän | | |
| 7510 | Arbetsgivaravgifter 31,42 % | | |
| 7832 | Avskrivningar på inventarier, verktyg och installationer | | |
| | **Summa** | | |

## Expected resultaträkning (owner fills in)

| Post | Belopp |
|---|---:|
| Nettoomsättning | |
| Råvaror och förnödenheter | |
| Handelsvaror | |
| Övriga externa kostnader | |
| Personalkostnader | |
| Av- och nedskrivningar av materiella och immateriella anläggningstillgångar | |
| **Rörelseresultat** | |
| Övriga ränteintäkter och liknande resultatposter | |
| Räntekostnader och liknande resultatposter | |
| **Resultat efter finansiella poster** | |
| Skatt på årets resultat | |
| **Årets resultat** | |

## Expected balansräkning (owner fills in)

| Post | Belopp |
|---|---:|
| Inventarier, verktyg och installationer | |
| Färdiga varor och handelsvaror | |
| Kundfordringar | |
| Övriga fordringar | |
| Förutbetalda kostnader och upplupna intäkter | |
| Kassa och bank | |
| **Summa tillgångar** | |
| Aktiekapital | |
| Balanserad vinst eller förlust | |
| Årets resultat | |
| Skulder till kreditinstitut | |
| Leverantörsskulder | |
| Skatteskulder | |
| Övriga skulder | |
| Upplupna kostnader och förutbetalda intäkter | |
| **Summa eget kapital och skulder** | |
