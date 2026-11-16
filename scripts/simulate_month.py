"""Post the reference solution for the whole simulator month through the service.

Creates a learner in a temporary SQLite database, books every document in the
Inkorg in date order with its key through services.simulator.submit, and
checks the result: every booking graded correct, the råbalans and the
balansräkning balance, and the bank account differs from the kontoutdrag by
exactly the two planted differences. Exits with status 1 on any failure.

Usage: python scripts/simulate_month.py [--seed N]
"""

import argparse
import os
import sys
import tempfile
from pathlib import Path

TEMP_DB = Path(tempfile.mkdtemp()) / "simulate_month.db"
os.environ["DATABASE_URL"] = f"sqlite:///{TEMP_DB}"

from ra.core.formatting import format_ore  # noqa: E402  (after DATABASE_URL is set)
from ra.core.money import Money, total  # noqa: E402
from ra.core.voucher import Side, VoucherLine  # noqa: E402
from ra.services import practice, simulator  # noqa: E402
from ra.services.views import RowInput  # noqa: E402
from ra.simulator.scenario import realise  # noqa: E402
from ra.storage import queries  # noqa: E402
from ra.storage.db import new_session  # noqa: E402

BANK = 1930


def _amount_text(money: Money) -> str:
    return f"{money.ore // 100},{money.ore % 100:02d}"


def _rows(voucher_lines: tuple[VoucherLine, ...]) -> list[RowInput]:
    return [RowInput(str(ln.account),
                     _amount_text(ln.amount) if ln.side is Side.DEBET else "",
                     _amount_text(ln.amount) if ln.side is Side.KREDIT else "")
            for ln in voucher_lines]


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--seed", type=int, default=None, help="run seed (default: random)")
    args = parser.parse_args()
    with new_session() as session, session.begin():
        learner_id = queries.create_learner(session, "simulate-month").id
        if args.seed is not None:
            queries.save_setting(session, learner_id, simulator.SEED_SETTING, args.seed)
    company = simulator.start(learner_id)
    with new_session() as session:
        seed = queries.learner_settings(session, learner_id)[simulator.SEED_SETTING]
    month = realise(simulator.scenario(), practice.recipe_context(), seed)
    keys = {r.event.id: r.result for r in month.events}
    print(f"{company.name}, {company.month}, seed {seed}")

    failures: list[str] = []
    while True:
        inbox = simulator.inbox(learner_id)
        pending = [item for item in inbox.items if item.status == simulator.STATUS_NEW]
        if not pending:
            break
        for item in pending:
            key = keys[item.event_id]
            result = simulator.submit(learner_id, item.event_id, _rows(key.voucher.lines),
                                      key.voucher.date, key.voucher.text, "sv")
            ok = result.feedback is not None and result.feedback.correct
            print(f"  {item.date:>18}  {result.voucher_label or '-':>5}  "
                  f"{'rätt' if ok else 'FEL'}  {item.title}")
            if not ok:
                failures.append(f"{item.event_id}: {result.problems or result.feedback}")
    if not simulator.inbox(learner_id).done:
        failures.append("the Inkorg still has documents that are not booked")

    reports = simulator.reports(learner_id)
    bank = next(a.closing for a in reports.ledger if a.number == BANK)
    planted = total([row.amount for row in month.planted])
    expected_bank = format_ore((month.statement_closing - planted).ore)

    print(f"Verifikationer: {len(reports.vouchers) - 1} och ingående balanser")
    print(f"Råbalans: debet {reports.trial_balance.total_debet}, "
          f"kredit {reports.trial_balance.total_kredit}, "
          f"{'balanserar' if reports.trial_balance.balanced else 'BALANSERAR INTE'}")
    print(f"Balansräkning: tillgångar {reports.balance.total_assets}, eget kapital och skulder "
          f"{reports.balance.total_equity_and_liabilities}")
    print(f"Årets resultat för månaden: {reports.income.net_result}")
    print(f"Bankkontot 1930: {bank}; kontoutdraget: {format_ore(month.statement_closing.ore)}; "
          f"de planterade raderna: {format_ore(planted.ore)}")
    for row in month.planted:
        print(f"  Planterad: {row.on_date} {row.text} {format_ore(row.amount.ore)}")
    if not reports.trial_balance.balanced:
        failures.append("the råbalans does not balance")
    if not reports.balance.balanced:
        failures.append("the balansräkning does not balance")
    if bank != expected_bank:
        failures.append(f"bank {bank} is not the kontoutdrag minus the planted rows, "
                        f"{expected_bank}")
    for failure in failures:
        print(f"FAILED: {failure}")
    print("OK: the month is booked" if not failures else f"FAILED: {len(failures)} problems")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
