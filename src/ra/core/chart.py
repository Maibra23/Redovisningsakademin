"""Kontoplan (chart of accounts) based on BAS-kontoplanen.

Each account has a four digit number whose first digit is its kontoklass
(class), a kind (tillgång, eget kapital, skuld, intäkt, kostnad), the side on
which it normally grows, the line in the resultaträkning or balansräkning it
belongs to, and an optional moms role used by the moms engine.
"""

from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any

import yaml

from ra.core.voucher import Side


class Kind(Enum):
    TILLGANG = "tillgang"
    EGET_KAPITAL = "eget_kapital"
    SKULD = "skuld"
    INTAKT = "intakt"
    KOSTNAD = "kostnad"


# Which kinds each kontoklass may hold in BAS: 1 tillgångar, 2 eget kapital och
# skulder, 3 rörelsens inkomster, 4 to 7 rörelsens kostnader, 8 finansiella poster.
KINDS_BY_CLASS: dict[int, frozenset[Kind]] = {
    1: frozenset({Kind.TILLGANG}),
    2: frozenset({Kind.EGET_KAPITAL, Kind.SKULD}),
    3: frozenset({Kind.INTAKT}),
    4: frozenset({Kind.KOSTNAD}),
    5: frozenset({Kind.KOSTNAD}),
    6: frozenset({Kind.KOSTNAD}),
    7: frozenset({Kind.KOSTNAD}),
    8: frozenset({Kind.INTAKT, Kind.KOSTNAD}),
}

MOMS_ROLES = frozenset({
    "utgaende_25", "utgaende_12", "utgaende_6", "utgaende_omvand_25",
    "ingaende", "ingaende_beraknad", "momsredovisning",
    "forsaljning_25", "forsaljning_12", "forsaljning_6", "forsaljning_momsfri",
    "forsaljning_eu_varor", "forsaljning_eu_tjanster",
    "inkop_eu_varor", "inkop_eu_tjanster",
})

REPORT_LINE_PREFIXES = ("rr.", "br.")


class ChartError(ValueError):
    """The kontoplan file is inconsistent."""


@dataclass(frozen=True)
class Account:
    """One konto in the kontoplan."""

    number: int
    name: str
    account_class: int
    kind: Kind
    normal_side: Side
    report_line: str
    moms_role: str | None = None


class Chart(Mapping[int, Account]):
    """Read only kontoplan: ``chart[1930]`` and ``1930 in chart``."""

    def __init__(self, accounts: Mapping[int, Account]) -> None:
        self._accounts = dict(accounts)

    def __getitem__(self, number: int) -> Account:
        return self._accounts[number]

    def __iter__(self) -> Iterator[int]:
        return iter(sorted(self._accounts))

    def __len__(self) -> int:
        return len(self._accounts)

    def by_moms_role(self, role: str) -> tuple[Account, ...]:
        """Accounts with the given moms role, in number order."""
        return tuple(a for n, a in sorted(self._accounts.items()) if a.moms_role == role)


def _parse_account(raw: Mapping[str, Any]) -> Account:
    try:
        account = Account(
            number=int(raw["number"]),
            name=str(raw["name"]),
            account_class=int(raw["class"]),
            kind=Kind(raw["kind"]),
            normal_side=Side(raw["normal_side"]),
            report_line=str(raw["report_line"]),
            moms_role=raw.get("moms_role"),
        )
    except (KeyError, ValueError, TypeError) as error:
        raise ChartError(f"Invalid account entry {dict(raw)!r}: {error}") from error
    _check_account(account)
    return account


def _check_account(account: Account) -> None:
    number = account.number
    if not 1000 <= number <= 9999:
        raise ChartError(f"{number}: account numbers have four digits")
    if number // 1000 != account.account_class:
        raise ChartError(f"{number}: first digit must equal class {account.account_class}")
    if account.kind not in KINDS_BY_CLASS.get(account.account_class, frozenset()):
        raise ChartError(f"{number}: kind {account.kind.value} does not fit class")
    if not account.name.strip():
        raise ChartError(f"{number}: missing name")
    if not account.report_line.startswith(REPORT_LINE_PREFIXES):
        raise ChartError(f"{number}: report line must start with rr. or br.")
    if account.moms_role is not None and account.moms_role not in MOMS_ROLES:
        raise ChartError(f"{number}: unknown moms role {account.moms_role}")


def chart_from_entries(entries: list[Mapping[str, Any]]) -> Chart:
    """Build and validate a kontoplan; account numbers must be unique."""
    accounts: dict[int, Account] = {}
    for raw in entries:
        account = _parse_account(raw)
        if account.number in accounts:
            raise ChartError(f"{account.number}: duplicate account number")
        accounts[account.number] = account
    return Chart(accounts)


def load_chart(path: Path) -> Chart:
    """Load ``content/kontoplan.yaml``."""
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not isinstance(data.get("accounts"), list):
        raise ChartError(f"{path}: expected a mapping with an 'accounts' list")
    return chart_from_entries(data["accounts"])
