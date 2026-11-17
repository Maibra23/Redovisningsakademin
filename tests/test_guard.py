"""The guard (architecture section 10): model text may only use supplied amounts."""

from ra.llm.guard import Problem, check

FACTS = (
    "Leverantörsfaktura från Sörby Möbelgrossist AB, 15 januari 2026.\n"
    "Netto 10 000,00 kr, moms 25 % 2 500,00 kr, att betala 12 500,00 kr.\n"
    "Rätt kontering: 4010 debet 10 000,00 kr, 2641 debet 2 500,00 kr, "
    "2440 kredit 12 500,00 kr.\n"
    "Ditt svar: 4010 debet 12 500,00 kr, 2440 kredit 12 500,00 kr. Felkod: MOMS_SAKNAS."
)


def test_guard_accepts_only_supplied_amounts() -> None:
    supplied = ("Du bokförde hela beloppet 12 500,00 kr som kostnad. Momsen på 2 500,00 kr "
                "ska i stället debiteras konto 2641, så kostnaden blir 10 000 kr.")
    invented = ("Du bokförde hela beloppet som kostnad. Momsen är 3 125,00 kr och ska "
                "debiteras konto 2641.")
    assert check(supplied, FACTS, max_words=120).ok
    assert check(invented, FACTS, max_words=120).problems == (Problem.AMOUNT,)
