"""Reference use cases: the Regelbibliotek and the Kontoplan, with search and filters.

Rules come from content/regler and accounts from content/kontoplan.yaml, the
subset of BAS-kontoplanen the app uses. The source block of the kontoplan is
read so the page can credit the BAS publication it was copied from.
"""

from collections.abc import Collection
from dataclasses import dataclass
from functools import lru_cache

import yaml

from ra.learning.schemas import Rule
from ra.paths import content_root
from ra.services import practice
from ra.services.formatting import format_date
from ra.services.lessons import rule_reference

CHART_FILE = "kontoplan.yaml"


@dataclass(frozen=True)
class RuleView:
    rule_id: str
    name: str
    section: str
    reference: str
    norm_type: str
    title: str
    explanation: str
    example: str
    in_practice: str
    source_url: str
    checked_on: str


@dataclass(frozen=True)
class AccountView:
    number: int
    name: str
    kind: str
    normal_side: str


@dataclass(frozen=True)
class AccountClassView:
    account_class: int
    accounts: tuple[AccountView, ...]


@dataclass(frozen=True)
class ChartSource:
    publication: str
    url: str
    checked_on: str


def _rule_view(rule: Rule) -> RuleView:
    return RuleView(rule.id, rule.namn, rule.lagrum, rule_reference(rule), rule.normtyp,
                    rule.titel, rule.forklaring, rule.exempel, rule.i_praktiken, rule.kalla,
                    format_date(rule.kontrollerad))


def _matches(query: str, *texts: str) -> bool:
    words = query.casefold().split()
    haystack = " ".join(texts).casefold()
    return all(word in haystack for word in words)


def norm_types(lang: str) -> tuple[str, ...]:
    """The types of norm that occur in the library, in a fixed order."""
    order = ("lag", "förordning", "allmänt råd", "vägledning", "myndighetsinformation")
    present = {r.normtyp for r in practice.library(lang).rules.values()}
    return tuple(n for n in order if n in present)


def rules(lang: str, query: str = "", types: Collection[str] = ()) -> tuple[RuleView, ...]:
    """Rule entries matching every word of ``query`` and one of ``types`` (all when empty)."""
    found = [r for r in practice.library(lang).rules.values()
             if (not types or r.normtyp in types)
             and _matches(query, r.id, r.namn, r.lagrum, r.titel, r.forklaring, r.exempel)]
    return tuple(_rule_view(r) for r in sorted(found, key=lambda r: (r.namn, r.id)))


def accounts(query: str = "") -> tuple[AccountClassView, ...]:
    """Accounts grouped by kontoklass; ``query`` matches number or name."""
    chart = practice.recipe_context().chart
    groups: dict[int, list[AccountView]] = {}
    for number in chart:
        account = chart[number]
        if _matches(query, str(number), account.name):
            groups.setdefault(account.account_class, []).append(AccountView(
                number, account.name, account.kind.value, account.normal_side.value))
    return tuple(AccountClassView(c, tuple(a)) for c, a in sorted(groups.items()))


@lru_cache(maxsize=1)
def chart_source() -> ChartSource:
    """Publication, address and check date of the BAS file the kontoplan was copied from."""
    data = yaml.safe_load((content_root() / CHART_FILE).read_text(encoding="utf-8"))
    source = data.get("source", {})
    return ChartSource(str(source.get("publication", "")), str(source.get("url", "")),
                       format_date(source["checked_on"]) if source.get("checked_on") else "")
