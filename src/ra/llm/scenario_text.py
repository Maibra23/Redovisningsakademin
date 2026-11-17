"""Nytt scenario: the model writes the story around an exercise (architecture section 10).

The model returns JSON with the counterparty's bransch and name, a concrete
description of the goods or service, and one situation sentence. Nothing in it
may hold a digit, so every amount and account still comes from the recipe; the
recipe's own description stays on the document as the category that decides
the account, and the model's description is only a detail after it. Answers
that fail validation, name a well known real company or cannot be had at all
fall back silently to the built in lists.
"""

import json
import random
import re
from collections.abc import Callable
from dataclasses import dataclass

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from ra.llm.guard import CJK, ENGLISH_MARKERS

MAX_TOKENS = 300
TEMPERATURE = 0.7
# A starting letter for the name, drawn by seed, gives each instance its own prompt.
LETTERS = "ABDEFGHKLMNOPRSTV"
COMPANY_FORMS = (" AB", " HB", " KB")


@dataclass(frozen=True)
class Role:
    """Who the counterparty is for a recipe, in the words the prompt uses."""

    name: str
    document: str
    category: str  # for documents without a description of their own (payments)
    situation: str


SUPPLIER = Role("leverantör", "en leverantörsfaktura eller en betalning till leverantören",
                "varor eller tjänster till ett kontor", "varför företaget köper av motparten")
CUSTOMER = Role("kund", "en kundfaktura, en kreditfaktura eller en inbetalning från kunden",
                "kontorsmöbler och tjänster för kontorsmiljö",
                "vad företaget har sålt till motparten")
SHOP = Role("butik", "ett kvitto på ett köp i butiken", "kontorsmateriel",
            "varför företaget köper i butiken")

# Recipes whose document has an outside counterparty in Sverige. Internal
# documents, Skatteverket, the bank, the landlord and EU trade keep their text.
ROLES: dict[str, Role] = {
    "leverantorsfaktura_kostnad": SUPPLIER,
    "leverantorsfaktura_varor": SUPPLIER,
    "utbetalning_leverantor": SUPPLIER,
    "inkop_inventarie": SUPPLIER,
    "inkop_forbrukningsinventarie": SUPPLIER,
    "forsaljning_faktura": CUSTOMER,
    "kreditfaktura": CUSTOMER,
    "inbetalning_kund": CUSTOMER,
    "kortkop_kvitto": SHOP,
    "utlagg": SHOP,
}

# Well known companies and authorities the model might borrow; a name containing one is refused.
BLOCKED_NAMES = (
    "ikea", "h&m", "hennes", "volvo", "ericsson", "spotify", "skanska", "ica", "coop", "axfood",
    "clas ohlson", "biltema", "jula", "bauhaus", "byggmax", "telia", "tele2", "telenor",
    "vattenfall", "seb", "swedbank", "handelsbanken", "nordea", "sas", "scania", "saab",
    "electrolux", "atlas copco", "sandvik", "skf", "essity", "ahlsell", "dustin", "staples",
    "lyreco", "office depot", "apple", "microsoft", "google", "amazon", "fortnox", "visma",
    "bokio", "postnord", "dhl", "bring", "systembolaget", "apoteket", "elgiganten", "netonnet",
    "webhallen", "åhléns", "ahlens", "lidl", "willys", "hemköp", "max", "mcdonald", "klarna",
    "ncc", "peab", "securitas", "hm", "lindex", "kappahl", "intersport", "stadium", "mediamarkt",
    "avanza", "nordnet", "länsförsäkringar", "folksam", "trygg", "ikano", "adecco", "manpower",
    "tieto", "cgi", "accenture", "kpmg", "pwc", "deloitte", "grant thornton", "bdo", "randstad",
    "inet", "kjell", "teknikmagasinet", "granngården", "mio", "jysk", "rusta", "polestar",
    "northvolt", "bolagsverket", "skatteverket", "posten", "schenker",
)
BLOCKED = re.compile(r"\b(?:" + "|".join(re.escape(n) for n in BLOCKED_NAMES) + r")\b",
                     flags=re.IGNORECASE)
FORBIDDEN = re.compile(r"\d|%|\bkr\b|\bkonto\b|[‒–—―−]| - |[{}<>]",
                       flags=re.IGNORECASE)
SITUATION_START = "Företaget "


class ScenarioText(BaseModel):
    """The model's story; every field short, plain Swedish, without figures."""

    model_config = ConfigDict(frozen=True, extra="forbid", str_strip_whitespace=True)

    bransch: str = Field(min_length=3, max_length=40)
    motpart: str = Field(min_length=5, max_length=45)
    beskrivning: str = Field(min_length=3, max_length=60)
    situation: str = Field(min_length=15, max_length=160)

    @field_validator("bransch", "motpart", "beskrivning", "situation")
    @classmethod
    def plain_swedish(cls, value: str) -> str:
        words = re.findall(r"[^\W\d_]+", value.lower())
        if FORBIDDEN.search(value) or CJK.search(value):
            raise ValueError("figures, markup or dashes")
        if sum(word in ENGLISH_MARKERS for word in words) >= 2:
            raise ValueError("English")
        return value

    @field_validator("motpart")
    @classmethod
    def invented_company(cls, value: str) -> str:
        if not value.endswith(COMPANY_FORMS):
            raise ValueError("no Swedish company form")
        if BLOCKED.search(value):
            raise ValueError("a well known company")
        return value

    @field_validator("situation")
    @classmethod
    def one_sentence_about_the_company(cls, value: str) -> str:
        if not value.startswith(SITUATION_START) or not value.endswith("."):
            raise ValueError("not a sentence about the company")
        if re.search(r"[.!?]\s", value):
            raise ValueError("more than one sentence")
        return value


@dataclass(frozen=True)
class Scenario:
    text: ScenarioText
    generated: bool


# Built in stories for when the model is off or its answer is refused. The
# names were checked for real companies in D5.1 or are the content's own.
FALLBACK_PARTIES = {
    SUPPLIER: (("Sörby Möbelgrossist AB", "Grosshandel"),
               ("Kvarnby Datahjälp AB", "IT-tjänster"),
               ("Ekbacka Kontorsservice AB", "Kontorsservice")),
    CUSTOMER: (("Fjällmo Arkitektkontor AB", "Arkitektverksamhet"),
               ("Gransjö Tandvårdsklinik AB", "Tandvård"),
               ("Tallbacka Fastighetsförvaltning AB", "Fastighetsförvaltning")),
    SHOP: (("Ljusbergs Kontorshandel AB", "Detaljhandel"),),
}
FALLBACK_SITUATIONS = {
    SUPPLIER: ("Företaget har beställt och fått leveransen enligt avtalet.",
               "Företaget har fått det som beställdes förra veckan."),
    CUSTOMER: ("Företaget har levererat det som kunden beställde enligt offerten.",
               "Företaget har utfört uppdraget som kunden beställde i början av månaden."),
    SHOP: ("Företaget behövde fylla på förrådet på kontoret.",),
}

PROMPT = """\
Skriv ett påhittat men vardagligt sammanhang till ett övningsunderlag i bokföring.
Företaget är ett svenskt aktiebolag. Underlaget är {document}.
Motparten är en {role} i Sverige. Varan eller tjänsten hör till kategorin "{category}".
Svara bara med ett JSON-objekt med nycklarna bransch, motpart, beskrivning och situation:
bransch: motpartens bransch med ett eller två vanliga ord, till exempel "kontorshandel".
motpart: ett påhittat svenskt företagsnamn som börjar på bokstaven {letter} och slutar på AB,
med högst tre ord, som inte liknar ett verkligt känt företag.
beskrivning: en vanlig vara eller tjänst som tydligt hör till kategorin "{category}",
med två till fem ord. Kontorsmateriel är förbrukningsvaror som papper, pärmar och pennor,
aldrig möbler, maskiner eller datorer.
situation: en kort mening som börjar med "Företaget" och säger {situation}, högst femton ord.
Använd bara vanliga svenska ord som finns i en ordbok. Hitta inte på nya ord. Kontrollera
att adjektiven böjs rätt efter substantivets genus.
Skriv korrekt svenska med å, ä och ö. Skriv inga siffror, inga belopp och inga konton.
Exempel för kategorin "Städtjänster": {{"bransch": "städtjänster", "motpart": "Lindbacka
Städservice AB", "beskrivning": "veckostädning av kontoret", "situation": "Företaget köper
städning eftersom kontoret har fått fler anställda."}}
"""
# Words that never belong under a consumables category; such a detail would
# contradict the account the recipe chose.
CONSUMABLE_CATEGORIES = ("kontorsmateriel", "förbrukningsmaterial")
NOT_CONSUMABLE = re.compile(
    r"(stol|bord|möbel|möbler|maskin|dator|skrivare|lampa|lampor|hylla|hyllor|skåp|telefon)",
    flags=re.IGNORECASE)


def supported(recipe: str) -> bool:
    return recipe in ROLES


def category(recipe: str, description: str | None) -> str:
    """The recipe's own description, or the role's general one."""
    return description or ROLES[recipe].category


def prompt(recipe: str, category: str, seed: int) -> str:
    role = ROLES[recipe]
    letter = LETTERS[random.Random(f"letter:{seed}").randrange(len(LETTERS))]
    return PROMPT.format(document=role.document, role=role.name, category=category,
                         letter=letter, situation=role.situation)


def parse(raw: str, category: str = "") -> ScenarioText:
    """The first JSON object in the model's answer, validated; raises ValueError."""
    match = re.search(r"\{.*\}", raw, flags=re.DOTALL)
    if match is None:
        raise ValueError("no JSON object")
    try:
        text = ScenarioText.model_validate(json.loads(match.group(0)))
    except (json.JSONDecodeError, ValidationError) as error:
        raise ValueError(str(error)) from error
    consumable = category.casefold() in CONSUMABLE_CATEGORIES
    if consumable and NOT_CONSUMABLE.search(f"{text.beskrivning} {text.situation}"):
        raise ValueError("equipment described as a consumable")
    return text


def fallback(recipe: str, category: str, seed: int) -> ScenarioText:
    role, rng = ROLES[recipe], random.Random(f"scenario:{recipe}:{seed}")
    name, trade = rng.choice(FALLBACK_PARTIES[role])
    return ScenarioText(bransch=trade, motpart=name, beskrivning=category,
                        situation=rng.choice(FALLBACK_SITUATIONS[role]))


def generate(recipe: str, category: str, seed: int,
             call: Callable[[str], str | None]) -> Scenario:
    """A story for one instance of ``recipe``; ``call`` sends a prompt and returns raw text.

    ``call`` returns None when the model is off or the budget is used up. Any
    refused answer gives the built in story, without a message.
    """
    raw = call(prompt(recipe, category, seed))
    if raw is not None:
        try:
            return Scenario(parse(raw, category), generated=True)
        except ValueError:
            pass
    return Scenario(fallback(recipe, category, seed), generated=False)
