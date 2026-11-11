"""Löner (payroll): nettolön, arbetsgivaravgifter and their verifikationer.

Bruttolön minus skatteavdrag is the nettolön paid to the employee. The
employer also pays arbetsgivaravgifter, a percentage of the bruttolön read by
date from ``content/parametrar.yaml``. Skatteavdrag and arbetsgivaravgifter
are paid to Skatteverket through the skattekonto. The tax withheld is an
input; tax tables are not modelled.
"""

import datetime as dt
from dataclasses import dataclass

from ra.core.money import Money, total
from ra.core.parameters import ParameterTable
from ra.core.voucher import Side, Voucher, VoucherLine

EMPLOYER_FEE_KEY = "arbetsgivaravgift_full"
SALARY_TEXT = "Löneutbetalning"
EMPLOYER_FEE_TEXT = "Arbetsgivaravgifter"
TAX_PAYMENT_TEXT = "Inbetalning till skattekontot"


class PayrollError(ValueError):
    """Payroll input is not valid."""


@dataclass(frozen=True)
class PayrollAccounts:
    """BAS accounts used by the payroll verifikationer (all in content/kontoplan.yaml)."""

    salary: int  # 7010 kollektivanställda or 7210 tjänstemän
    employer_fee: int = 7510
    tax_withheld: int = 2710
    employer_fee_liability: int = 2731
    bank: int = 1930
    tax_account: int = 1630


@dataclass(frozen=True)
class Payslip:
    """One employee's bruttolön, skatteavdrag, nettolön and arbetsgivaravgifter."""

    gross: Money
    tax_withheld: Money
    net: Money
    employer_fee: Money


def calculate(
    gross: Money, tax_withheld: Money, on_date: dt.date, params: ParameterTable
) -> Payslip:
    """Nettolön = bruttolön - skatteavdrag; arbetsgivaravgifter = bruttolön x avgiftssats."""
    if gross.ore < 0 or tax_withheld.ore < 0:
        raise PayrollError("Bruttolön and skatteavdrag cannot be negative")
    if tax_withheld > gross:
        raise PayrollError("Skatteavdrag cannot exceed bruttolön")
    fee = gross.percent(params.value_for(EMPLOYER_FEE_KEY, on_date))
    return Payslip(gross=gross, tax_withheld=tax_withheld, net=gross - tax_withheld,
                   employer_fee=fee)


@dataclass(frozen=True)
class PayrollVouchers:
    """The three verifikationer of one pay run."""

    salary: Voucher
    employer_fee: Voucher
    tax_payment: Voucher


def vouchers(
    employees: list[tuple[Money, Money]],
    salary_on: dt.date,
    payment_on: dt.date,
    params: ParameterTable,
    accounts: PayrollAccounts,
    series: str = "L",
) -> PayrollVouchers:
    """Löneverifikation, arbetsgivaravgifter and the payment to the skattekonto.

    ``employees`` holds (bruttolön, skatteavdrag) per person. Arbetsgivaravgifter
    are computed on the summed bruttolön, as on the arbetsgivardeklaration.
    1. Lön: debet lönekonto (brutto), kredit personalskatt (skatteavdrag) and bank (netto).
    2. Arbetsgivaravgifter: debet kostnad, kredit skuld.
    3. Inbetalning: debet skattekonto, kredit bank, with skatteavdrag plus avgifter.
    The later debitering on the skattekonto (debet 2710 and 2731, kredit 1630) is
    its own verifikation when Skatteverket charges the account.
    """
    if not employees:
        raise PayrollError("A pay run needs at least one employee")
    slips = [calculate(gross, tax, salary_on, params) for gross, tax in employees]
    gross = total([s.gross for s in slips])
    tax = total([s.tax_withheld for s in slips])
    net = gross - tax
    fee = gross.percent(params.value_for(EMPLOYER_FEE_KEY, salary_on))
    salary_lines = (
        VoucherLine(accounts.salary, Side.DEBET, gross),
        VoucherLine(accounts.tax_withheld, Side.KREDIT, tax),
        VoucherLine(accounts.bank, Side.KREDIT, net),
    )
    fee_lines = (
        VoucherLine(accounts.employer_fee, Side.DEBET, fee),
        VoucherLine(accounts.employer_fee_liability, Side.KREDIT, fee),
    )
    payment_lines = (
        VoucherLine(accounts.tax_account, Side.DEBET, tax + fee),
        VoucherLine(accounts.bank, Side.KREDIT, tax + fee),
    )
    return PayrollVouchers(
        salary=Voucher(series, salary_on, SALARY_TEXT, tuple(ln for ln in salary_lines
                                                             if ln.amount.ore > 0)),
        employer_fee=Voucher(series, salary_on, EMPLOYER_FEE_TEXT, fee_lines),
        tax_payment=Voucher(series, payment_on, TAX_PAYMENT_TEXT, payment_lines),
    )
