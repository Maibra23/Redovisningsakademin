"""Förklara med andra ord and Fråga handledaren (PRD section 10, architecture section 10).

Both work on an exercise the grader has already decided. The facts are the
exercise as the learner saw it, the learner's answer, the grade with its error
codes, the feedback's correct treatment, the rule entry and the tip, all as the
engine and the content wrote them. The model only rewords; ``services.ai`` runs
the guard, and on any failure the page keeps the built in feedback alone.
"""

import re

from ra.services import ai, practice
from ra.services.views import (
    DocumentView,
    SubmitResult,
    TutorReply,
    TutorStatus,
    VoucherView,
)

EXPLAIN_WORDS = 120
ANSWER_WORDS = 120
QUESTION_CHARS = 300
# The model writes this marker instead of an answer to an off topic question;
# the page then shows its own polite refusal, so the refusal is always correct Swedish.
OFF_TOPIC = "[UTANFÖR]"
OFF_TOPIC_PATTERN = re.compile(r"\[?UTANF[ÖO]R\]?")

STATUS = {
    ai.AiStatus.OK: TutorStatus.OK,
    ai.AiStatus.SESSION_FULL: TutorStatus.SESSION_FULL,
    ai.AiStatus.DAILY_FULL: TutorStatus.DAILY_FULL,
}

EXPLAIN_TASK = {
    "sv": ("Förklara med andra ord för eleven vad som blev fel i just det här svaret och "
           "varför. Jämför elevens svar rad för rad med den rätta verifikationen och använd "
           "förklaringen under Vad som blev fel och Varför. Lägg inte till egna skäl. Skriv "
           "tre till fem korta meningar löpande text, högst {words} ord."),
    "en": ("Explain to the learner in other words what went wrong in this particular answer "
           "and why. Compare the learner's answer line by line with the correct verifikation "
           "and use the explanation under Vad som blev fel and Varför. Add no reasons of your "
           "own. Write three to five short sentences of running text in English, at most "
           "{words} words."),
}
ANSWER_TASK = {
    "sv": ("Eleven ställer en fråga om uppgiften: \"{question}\"\n"
           "Svara bara med det som står i underlaget, i tre till fem korta meningar löpande "
           "text, högst {words} ord. Lägg inte till egna skäl. Om underlaget inte räcker för "
           "att svara, säg det. Om frågan inte handlar om den här uppgiften eller redovisningen "
           "i den, svara bara {marker}"),
    "en": ("The learner asks a question about the exercise: \"{question}\"\n"
           "Answer only with what the facts say, in three to five short sentences of English "
           "running text, at most {words} words. Add no reasons of your own. If the facts are "
           "not enough to answer, say so. If the question is not about this exercise or the "
           "accounting in it, answer only {marker}"),
}


def available() -> bool:
    """True when the AI controls may be shown."""
    return ai.available()


def _voucher_lines(view: VoucherView) -> list[str]:
    return [f"{row.account} {row.name} "
            + (f"debet {row.debet}" if row.debet else f"kredit {row.kredit}")
            for row in view.rows]


def _document_lines(document: DocumentView) -> list[str]:
    lines = [f"Underlag: {document.title}, {document.date}"]
    if document.counterparty:
        lines.append(f"Motpart: {document.counterparty}")
    if document.text:
        lines.append(document.text)
    lines += [f"{label}: {amount if amount is not None else 'att beräkna'}"
              for label, amount in (*document.rows, *document.totals)]
    return lines


def facts(lang: str, exercise_id: str, seed: int, result: SubmitResult) -> str:
    """Everything the model may use, as text; the guard checks the answer against it."""
    view = practice.exercise_view(lang, exercise_id, seed)
    exercise = practice.instance(lang, exercise_id, seed).exercise
    rule = practice.library(lang).rules[exercise.regel]
    feedback = result.feedback
    lines = [f"Uppgiftstyp: {view.typ}"]
    lines += [text for text in (view.instruction, view.question) if text]
    lines += [f"Alternativ: {option}" for option in view.options]
    lines += [f"Post att placera: {item}" for item in view.items]
    lines += [f"Grupp: {group}" for group in view.categories]
    if view.document is not None:
        lines += _document_lines(view.document)
    if view.booked is not None:
        lines += ["Bokförd verifikation med ett fel:", *_voucher_lines(view.booked)]
    lines += [f"Rad på kontoutdraget: {s.date}, {s.text}, {s.amount}" for s in view.statement]
    lines += [f"Rad i huvudboken, konto 1930: {s.date}, {s.text}, {s.amount}"
              for s in view.ledger]
    lines += ["Elevens svar:", *(result.answer or ("inget svar",))]
    if feedback is not None:
        lines.append(f"Bedömning: {'rätt' if feedback.correct else 'fel'}")
        if feedback.codes:
            lines.append(f"Felkoder: {', '.join(feedback.codes)}")
        lines += [f"Vad som blev fel: {feedback.what}", f"Varför: {feedback.why}"]
        lines.append(f"Rätt hantering: {feedback.treatment}")
        if feedback.treatment_voucher is not None:
            lines += _voucher_lines(feedback.treatment_voucher)
        lines += list(feedback.notes)
        lines.append(f"Tips: {feedback.tip}")
    lines.append(f"Regel: {rule.namn} {rule.lagrum}, {rule.titel}. {rule.forklaring}")
    return "\n".join(lines)


def _reply(reply: ai.AiReply) -> TutorReply:
    if reply.text is not None and OFF_TOPIC_PATTERN.search(reply.text):
        return TutorReply(None, TutorStatus.DECLINED)
    return TutorReply(reply.text, STATUS.get(reply.status, TutorStatus.NOT_AVAILABLE))


def explain(lang: str, exercise_id: str, seed: int, result: SubmitResult) -> TutorReply:
    """The graded mistake explained in other words, at most 120 words."""
    if result.feedback is None or result.feedback.correct:
        return TutorReply(None, TutorStatus.NOT_AVAILABLE)
    task = EXPLAIN_TASK.get(lang, EXPLAIN_TASK["sv"]).format(words=EXPLAIN_WORDS)
    return _reply(ai.ask(task, facts(lang, exercise_id, seed, result), max_words=EXPLAIN_WORDS,
                         language=lang))


def clean_question(question: str) -> str:
    """The learner's question on one line, length limited; it is never shown as HTML."""
    return " ".join(question.split())[:QUESTION_CHARS]


def answer(lang: str, exercise_id: str, seed: int, result: SubmitResult,
           question: str) -> TutorReply:
    """An answer to the learner's question from the exercise's facts only."""
    asked = clean_question(question).replace('"', "'")
    if not asked:
        return TutorReply(None, TutorStatus.NOT_AVAILABLE)
    task = ANSWER_TASK.get(lang, ANSWER_TASK["sv"]).format(question=asked, words=ANSWER_WORDS,
                                                           marker=OFF_TOPIC)
    return _reply(ai.ask(task, facts(lang, exercise_id, seed, result), max_words=ANSWER_WORDS,
                         language=lang))
