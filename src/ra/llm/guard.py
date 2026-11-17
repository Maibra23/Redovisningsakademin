"""Guard: model text is shown only when it holds to the supplied facts.

Architecture section 10. The facts are the text the model was given, read
with the same rules as its answer, so "supplied" means written in the facts:

* every amount in the answer is an amount in the facts (compared in öre);
* every four digit number (an account number, or a year) is in the facts;
* every rate (a number before "%" or "procent") is in the facts;
* any other number of three or more digits is in the facts;
* no law name, abbreviation, chapter or paragraph that the facts do not contain;
* at most ``max_words`` words, and not empty;
* Swedish text: no Chinese, Japanese or Korean characters, and no run of
  English (three English function words within eight words); in English
  mode only the first part applies;
* no thinking block left over.
"""

import re
from dataclasses import dataclass, field
from enum import StrEnum


class Problem(StrEnum):
    EMPTY = "empty"
    THINKING = "thinking"
    AMOUNT = "amount"
    ACCOUNT = "four_digit"
    RATE = "rate"
    NUMBER = "number"
    LAW = "law"
    LENGTH = "length"
    LANGUAGE = "language"


# A number: grouped thousands (12 500) or plain digits, with an optional decimal part.
NUMBER = re.compile(r"(?<![\w,.])(\d{1,3}(?:[  ]\d{3})+|\d+)(?:,(\d+))?(?![\w])")
CURRENCY = re.compile(r"\s*(?:kr|kronor|SEK)\b")
PERCENT = re.compile(r"\s*(?:%|procent)")

LAW_NAMES = re.compile(
    r"\b(bokförings|årsredovisnings|mervärdesskatte|moms|skatteförfarande|inkomstskatte|"
    r"socialavgifts|aktiebolags)lag(?:en|ens)?\b",
    flags=re.IGNORECASE,
)
LAW_ABBREVIATIONS = re.compile(r"\b(BFL|ÅRL|ML|SFL|IL|SAL|ABL|BFNAR|BFN|K2|K3)\b")
CHAPTER = re.compile(r"\b(\d+)\s*kap\b\.?", flags=re.IGNORECASE)
SECTION = re.compile(r"(\d+)\s*§|§\s*(\d+)")

CJK = re.compile(r"[぀-ヿ㐀-䶿一-鿿가-힯]")
ENGLISH_MARKERS = frozenset({
    "the", "and", "is", "are", "this", "that", "these", "those", "with", "you", "your",
    "of", "to", "which", "will", "would", "should", "have", "has", "was", "were", "from",
    "they", "their", "there", "what", "when", "where", "because", "into", "been", "does",
})
ENGLISH_WINDOW = 8
ENGLISH_LIMIT = 3
CHECKED_DIGITS = 3


@dataclass(frozen=True)
class Claims:
    """The figures and references one text contains."""

    amounts: frozenset[int] = frozenset()  # öre
    four_digit: frozenset[int] = frozenset()
    rates: frozenset[str] = frozenset()
    numbers: frozenset[int] = frozenset()
    laws: frozenset[str] = frozenset()


@dataclass(frozen=True)
class GuardResult:
    problems: tuple[Problem, ...] = ()
    details: tuple[str, ...] = field(default=())

    @property
    def ok(self) -> bool:
        return not self.problems


def _ore(whole: str, decimals: str) -> int:
    return int(whole) * 100 + int(decimals.ljust(2, "0"))


def read_claims(text: str) -> Claims:
    amounts: set[int] = set()
    four_digit: set[int] = set()
    rates: set[str] = set()
    numbers: set[int] = set()
    for match in NUMBER.finditer(text):
        raw_whole, decimals = match.group(1), match.group(2) or ""
        whole = re.sub(r"[  ]", "", raw_whole)
        after = text[match.end():]
        if PERCENT.match(after):
            significant = decimals.rstrip("0")
            rates.add(f"{int(whole)},{significant}" if significant else str(int(whole)))
        elif len(decimals) > 2:
            numbers.add(int(whole))
        elif CURRENCY.match(after) or decimals or whole != raw_whole:
            amounts.add(_ore(whole, decimals))
        elif len(whole) == 4:
            four_digit.add(int(whole))
        else:
            numbers.add(int(whole))
    return Claims(frozenset(amounts), frozenset(four_digit), frozenset(rates),
                  frozenset(numbers), _laws(text))


def _laws(text: str) -> frozenset[str]:
    found = {f"lag:{m.group(1).lower()}" for m in LAW_NAMES.finditer(text)}
    found |= {f"förkortning:{m.group(1)}" for m in LAW_ABBREVIATIONS.finditer(text)}
    found |= {f"kap:{m.group(1)}" for m in CHAPTER.finditer(text)}
    found |= {f"§:{m.group(1) or m.group(2)}" for m in SECTION.finditer(text)}
    if "§" in text and not SECTION.search(text):
        found.add("§")
    return frozenset(found)


def _english_run(words: list[str]) -> bool:
    flags = [word.lower() in ENGLISH_MARKERS for word in words]
    return any(sum(flags[i:i + ENGLISH_WINDOW]) >= ENGLISH_LIMIT
               for i in range(max(1, len(flags) - ENGLISH_WINDOW + 1)))


def _figures(answer: Claims, facts: Claims) -> list[tuple[Problem, str]]:
    whole_kronor = {ore // 100 for ore in facts.amounts if ore % 100 == 0}
    known_integers = facts.numbers | facts.four_digit | whole_kronor
    found = [(Problem.AMOUNT, str(a)) for a in sorted(answer.amounts - facts.amounts)]
    found += [(Problem.ACCOUNT, str(n)) for n in sorted(answer.four_digit - known_integers)]
    found += [(Problem.RATE, r) for r in sorted(answer.rates - facts.rates)]
    found += [(Problem.NUMBER, str(n)) for n in sorted(answer.numbers - known_integers)
              if len(str(n)) >= CHECKED_DIGITS]
    found += [(Problem.LAW, law) for law in sorted(answer.laws - facts.laws)]
    return found


def check(text: str, facts: str, max_words: int, language: str = "sv") -> GuardResult:
    """Every problem with ``text`` as an answer built on ``facts``; none means show it."""
    words = re.findall(r"[^\W\d_]+", text)
    if not text.strip():
        return GuardResult((Problem.EMPTY,))
    found: list[tuple[Problem, str]] = []
    if "<think>" in text or "</think>" in text:
        found.append((Problem.THINKING, ""))
    found += _figures(read_claims(text), read_claims(facts))
    if len(text.split()) > max_words:
        found.append((Problem.LENGTH, str(len(text.split()))))
    if CJK.search(text) or (language == "sv" and _english_run(words)):
        found.append((Problem.LANGUAGE, ""))
    problems = tuple(dict.fromkeys(problem for problem, _ in found))
    return GuardResult(problems, tuple(f"{p.name} {d}".strip() for p, d in found))
