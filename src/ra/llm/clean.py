"""Cleaning step for model text, run before the guard (architecture section 10).

Adapted from utils/humanizer.py in the owner's ekonomistyrning repository. It
never calls the model: it removes known stiff phrases, Markdown headings and
LaTeX, replaces dashes used as punctuation (the owner's style rule), and turns
English number formatting into Swedish so the guard reads every amount alike.
"""

import re

NBSP = "\u00a0"

# Stiff phrases a Swedish reader recognises as machine written. Each is
# removed with the comma or space that follows it.
STIFF_PHRASES = (
    r"det är viktigt att notera att",
    r"det bör betonas att",
    r"sammanfattningsvis",
    r"för att sammanfatta",
    r"som tidigare nämnts",
    r"i ett nötskal",
    r"hoppas det(ta)? hjälper",
    r"tveka inte att fråga",
    r"låt mig veta om du har (fler|några) frågor",
)
STIFF = re.compile(r"\b(?:" + "|".join(STIFF_PHRASES) + r")\b[,:.!]?\s*", flags=re.IGNORECASE)

HEADING = re.compile(r"^#{1,6}[ \t]+(.+?)[ \t]*#*[ \t]*$", flags=re.MULTILINE)
LATEX_TEXT = re.compile(r"\\(?:text|mathrm|mathbf|operatorname)\s*\{([^{}]*)\}")
LATEX_REST = re.compile(r"\$\$|\$|\\\(|\\\)|\\\[|\\\]|\\[a-zA-Z]+|[{}]")

# "599 kr - 325 kr": a subtraction, written out so it is not read as a dash.
SUBTRACTION = re.compile(r"(\d(?:[ \u00a0]?kr)?)[ \t]+[-\u2012\u2013\u2014\u2212][ \t]+(?=\d)")
# A dash glued to a digit is a minus sign; anything else between words is punctuation.
MINUS_SIGN = re.compile(r"[\u2012\u2013\u2014\u2015\u2212](?=\d)")
DASH = re.compile(r"\s*[\u2012\u2013\u2014\u2015\u2212]\s*|\s+-\s+")

EN_GROUPED = re.compile(r"(?<![\w.,])(\d{1,3}(?:,\d{3})+)(?:\.(\d{1,2}))?(?![\w,])")
EN_DECIMAL = re.compile(r"(?<![\w.,])(\d+)\.(\d{1,2})(?![\w.,]|\.\w)")


def _sentence_case(match: re.Match[str]) -> str:
    return match.group(1) + match.group(2).upper()


def remove_stiff_phrases(text: str) -> str:
    cleaned = STIFF.sub("", text)
    # A sentence that began with a removed phrase starts with a capital again.
    return re.sub(r"(^|[.!?]\s+)([a-zåäö])", _sentence_case, cleaned, flags=re.MULTILINE)


def remove_markup(text: str) -> str:
    """Headings become plain lines; LaTeX commands and delimiters go."""
    cleaned = HEADING.sub(r"\1", text)
    cleaned = LATEX_TEXT.sub(r"\1", cleaned)
    return LATEX_REST.sub("", cleaned)


def replace_dashes(text: str) -> str:
    cleaned = SUBTRACTION.sub(r"\1 minus ", text)
    cleaned = MINUS_SIGN.sub("-", cleaned)
    cleaned = DASH.sub(", ", cleaned)
    return re.sub(r",\s*,", ",", cleaned)


def swedish_numbers(text: str) -> str:
    """1,234.56 becomes 1 234,56 and 12.5 becomes 12,5."""
    def grouped(match: re.Match[str]) -> str:
        whole = match.group(1).replace(",", " ")
        return f"{whole},{match.group(2)}" if match.group(2) else whole

    cleaned = EN_GROUPED.sub(grouped, text)
    return EN_DECIMAL.sub(r"\1,\2", cleaned)


def clean(text: str) -> str:
    cleaned = remove_markup(text)
    cleaned = remove_stiff_phrases(cleaned)
    cleaned = replace_dashes(cleaned)
    cleaned = swedish_numbers(cleaned).replace(NBSP, " ")
    cleaned = re.sub(r"[^\S\n]{2,}", " ", cleaned)
    cleaned = re.sub(r"[^\S\n]+([,.;:!?])", r"\1", cleaned)
    return re.sub(r"\n{3,}", "\n\n", cleaned).strip()
