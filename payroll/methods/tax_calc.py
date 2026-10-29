"""
Module: payroll.tax_calc

This module contains a function for calculating the taxable amount for an employee
based on their contract details and income information.
"""

import datetime
import logging
import math

from payroll.methods.methods import (
    compute_yearly_taxable_amount,
    convert_year_tax_to_period,
)
from payroll.methods.payslip_calc import (
    calculate_gross_pay,
    calculate_taxable_gross_pay,
)
from payroll.methods.safe_tax_code import run_tax_code
from payroll.models.models import Contract
from payroll.models.tax_models import TaxBracket

logger = logging.getLogger(__name__)


def calculate_bracket_annual_tax(yearly_income: float, filing) -> float:
    """
    Resolve annual tax from DB brackets for a filing status.

    Uses slab semantics matching income-tax calculators:

        fixed_amount + (yearly_income - min_income) * tax_rate / 100

    Only the single matching bracket (income exceeds min, does not exceed max)
    is applied. Brackets with no upper limit use an infinite max.
    """
    if yearly_income is None or yearly_income <= 0:
        return 0.0

    tax_brackets = TaxBracket.objects.filter(filing_status_id=filing).order_by(
        "min_income"
    )
    if not tax_brackets.exists():
        return 0.0

    income = float(yearly_income)
    matching = None
    for bracket in tax_brackets:
        upper = bracket.max_income if bracket.max_income is not None else math.inf
        if income > float(bracket.min_income) and income <= float(upper):
            matching = bracket
            break

    # Income at or below the first threshold (e.g. 0) → no tax.
    if matching is None:
        first = tax_brackets.first()
        if first and income <= float(first.min_income):
            return 0.0
        # Above every defined max — apply the last (open-ended) bracket if any.
        last = tax_brackets.last()
        if last and (
            last.max_income is None
            or last.max_income == math.inf
            or income > float(last.max_income)
        ):
            matching = last
        else:
            return 0.0

    return matching.calculate_annual_tax(income)


def calculate_taxable_amount(**kwargs):
    """Calculate the taxable amount for a given employee within a specific period.

    Args:
        employee (int): The ID of the employee.
        start_date (datetime.date): The start date of the period.
        end_date (datetime.date): The end date of the period.
        allowances (int): The number of allowances claimed by the employee.
        total_allowance (float): The total allowance amount.
        basic_pay (float): The basic pay amount.
        day_dict (dict): A dictionary containing specific day-related information.

    Returns:
        float: The federal tax amount for the specified period.
    """
    employee = kwargs["employee"]
    start_date = kwargs["start_date"]
    end_date = kwargs["end_date"]
    basic_pay = kwargs["basic_pay"]
    contract = Contract.objects.filter(
        employee_id=employee, contract_status="active"
    ).first()
    filing = contract.filing_status if contract else None
    if not filing:
        return 0
    tax_brackets = TaxBracket.objects.filter(filing_status_id=filing).order_by(
        "min_income"
    )
    num_days = (end_date - start_date).days + 1
    calculation_functions = {
        "taxable_gross_pay": calculate_taxable_gross_pay,
        "gross_pay": calculate_gross_pay,
    }
    based = filing.based_on
    if based in calculation_functions:
        calculation_function = calculation_functions[based]
        income = calculation_function(**kwargs)
        income = float(income[based])
    else:
        income = float(basic_pay)

    year = end_date.year
    check_start_date = datetime.date(year, 1, 1)
    check_end_date = datetime.date(year, 12, 31)
    total_days = (check_end_date - check_start_date).days + 1
    # Monthly wage contracts annualize as 12 × period income (matches
    # salaried income-tax calculators). Other wage types keep day proration.
    is_monthly = bool(contract and contract.wage_type == "monthly")
    if is_monthly:
        yearly_income = float(income) * 12
    else:
        yearly_income = income / num_days * total_days
    yearly_income = compute_yearly_taxable_amount(income, yearly_income)
    yearly_income = round(yearly_income, 2)
    federal_tax = 0
    if filing is not None and not filing.use_py:
        federal_tax = calculate_bracket_annual_tax(yearly_income, filing)

    elif filing.use_py:
        try:
            federal_tax = run_tax_code(filing.python_code, yearly_income)
        except Exception as e:
            logger.error(e)

    federal_tax_for_period = 0
    if federal_tax and (tax_brackets.exists() or filing.use_py):
        if is_monthly:
            federal_tax_for_period = federal_tax / 12.0
        else:
            daily_federal_tax = federal_tax / total_days
            federal_tax_for_period = daily_federal_tax * num_days

    federal_tax_for_period = convert_year_tax_to_period(
        federal_tax_for_period=federal_tax_for_period,
        yearly_tax=federal_tax,
        total_days=total_days,
        start_date=start_date,
        end_date=end_date,
    )
    return federal_tax_for_period
