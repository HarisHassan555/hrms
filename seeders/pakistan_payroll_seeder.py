"""
Payroll master data and transactional samples for DSG Pakistan companies.

Sets currency to PKR, Pakistan-style tax slabs, allowances/deductions,
salary structures, contract links, and the last three monthly payslips.
Idempotent — safe to re-run.
"""

from __future__ import annotations

import json
from datetime import date, timedelta

from dateutil.relativedelta import relativedelta
from django.db import transaction
from django.utils import timezone

from base.models import Company
from employee.models import Employee, EmployeeWorkInformation
from payroll.methods.methods import calculate_employer_contribution, save_payslip
from payroll.models.models import (
    Contract,
    Deduction,
    EncashmentGeneralSettings,
    FilingStatus,
    LoanAccount,
    PayrollGeneralSetting,
    Payslip,
    PayslipAutoGenerate,
    SalaryStructure,
)
from payroll.models.tax_models import PayrollSettings, TaxBracket
from payroll.views.component_views import payroll_calculation

from .utils import SeederResult, record, set_m2m, upsert

DSG_COMPANY_NAMES = ("DSG Technologies", "DSG Business Solutions")
EMAIL_DOMAIN = "dsg.pk"

CURRENCY_SYMBOL = "PKR"
CURRENCY_POSITION = "prefix"

FILING_STATUS_NAME = "Pakistan — Salaried Individual"
SALARY_STRUCTURE_TITLE = "DSG Pakistan Monthly Package"

# Pakistan individual income tax slabs (annual PKR, simplified FY demo).
PK_TAX_SLABS = (
    (0, 600_000, 0, 0),
    (600_000, 1_200_000, 5, 0),
    (1_200_000, 2_200_000, 15, 30_000),
    (2_200_000, 3_200_000, 25, 180_000),
    (3_200_000, 4_100_000, 30, 430_000),
    (4_100_000, None, 35, 700_000),
)

ALLOWANCE_SPECS = (
    {
        "title": "Housing Allowance",
        "amount": 25_000,
        "is_taxable": True,
    },
    {
        "title": "Transport Allowance",
        "amount": 10_000,
        "is_taxable": False,
    },
    {
        "title": "Medical Allowance",
        "amount": 8_000,
        "is_taxable": False,
    },
    {
        "title": "Utility Allowance",
        "amount": 5_000,
        "is_taxable": True,
    },
    {
        "title": "Mobile / Internet Allowance",
        "amount": 3_000,
        "is_taxable": False,
    },
)

DEDUCTION_SPECS = (
    {
        "title": "EOBI (Employee)",
        "is_fixed": True,
        "amount": 400,
        "is_pretax": True,
        "is_tax": False,
    },
    {
        "title": "Provident Fund (8%)",
        "is_fixed": False,
        "rate": 8.0,
        "based_on": "basic_pay",
        "is_pretax": True,
        "is_tax": False,
    },
    {
        "title": "Professional Tax",
        "is_fixed": True,
        "amount": 200,
        "is_pretax": False,
        "is_tax": False,
    },
)

LOAN_SPECS = (
    {
        "email": f"rehan.malik@{EMAIL_DOMAIN}",
        "title": "Salary advance — Ramadan",
        "loan_amount": 50_000,
        "installments": 5,
        "installment_amount": 10_000,
    },
)


def _dsg_companies() -> list[Company]:
    return list(Company.objects.filter(company__in=DSG_COMPANY_NAMES).order_by("pk"))


def _employees(companies: list[Company]) -> list[Employee]:
    return list(
        Employee.objects.filter(
            is_active=True,
            employee_work_info__company_id__in=companies,
        )
        .distinct()
        .order_by("pk")
    )


def _employee_by_email(email: str) -> Employee | None:
    return Employee.objects.filter(email=email, is_active=True).order_by("pk").first()


def _ensure_global_currency(result: SeederResult) -> None:
    """Align legacy/global payroll settings row used when no company is set."""
    settings, status = upsert(
        PayrollSettings,
        {"company_id": None},
        {
            "currency_symbol": CURRENCY_SYMBOL,
            "position": CURRENCY_POSITION,
        },
    )
    record(result, status, "Default payroll currency", settings)


def _ensure_payroll_settings(company: Company, result: SeederResult) -> None:
    settings, status = upsert(
        PayrollSettings,
        {"company_id": company},
        {
            "currency_symbol": CURRENCY_SYMBOL,
            "position": CURRENCY_POSITION,
        },
    )
    record(result, status, "Payroll settings (PKR)", company)

    general, status = upsert(
        PayrollGeneralSetting,
        {"company_id": company},
        {"notice_period": 30},
    )
    record(result, status, "Payroll general setting", company)

    auto, status = upsert(
        PayslipAutoGenerate,
        {"company_id": company},
        {"generate_day": "last day", "auto_generate": False},
    )
    record(result, status, "Payslip automation", company)


def _ensure_encashment_settings(result: SeederResult) -> None:
    row = EncashmentGeneralSettings.objects.order_by("pk").first()
    defaults = {
        "bonus_amount": 500,
        "leave_amount": 4500,
        "leave_encashment_enabled": True,
        "is_applicable_to_all": True,
    }
    if row is None:
        row = EncashmentGeneralSettings.objects.create(**defaults)
        record(result, "created", "Encashment settings", row)
        return
    changed = False
    for field, value in defaults.items():
        if getattr(row, field) != value:
            setattr(row, field, value)
            changed = True
    if changed:
        row.save()
        record(result, "updated", "Encashment settings", row)
    else:
        record(result, "existing", "Encashment settings", row)


def _ensure_filing_and_tax(company: Company, result: SeederResult) -> FilingStatus:
    filing, status = upsert(
        FilingStatus,
        {"filing_status": FILING_STATUS_NAME, "company_id": company},
        {
            "based_on": "taxable_gross_pay",
            "use_py": False,
            "description": "Pakistan salaried individual — demo FY slabs (PKR).",
        },
    )
    record(result, status, "Filing status", filing)

    for min_income, max_income, rate, fixed in PK_TAX_SLABS:
        lookup = {"filing_status_id": filing, "min_income": float(min_income)}
        bracket, b_status = upsert(
            TaxBracket,
            lookup,
            {
                "max_income": float(max_income) if max_income is not None else None,
                "tax_rate": float(rate),
                "fixed_amount": float(fixed),
            },
        )
        record(result, b_status, "Tax bracket", bracket)
    return filing


def _ensure_allowances(company: Company, result: SeederResult) -> list:
    from payroll.models.models import Allowance

    items = []
    for spec in ALLOWANCE_SPECS:
        allowance, status = upsert(
            Allowance,
            {"title": spec["title"], "company_id": company},
            {
                "include_active_employees": True,
                "is_taxable": spec["is_taxable"],
                "is_fixed": True,
                "is_condition_based": False,
                "amount": float(spec["amount"]),
                "only_show_under_employee": False,
            },
        )
        record(result, status, "Allowance", f"{allowance} @ {company}")
        items.append(allowance)
    return items


def _ensure_deductions(company: Company, result: SeederResult) -> list:
    items = []
    for spec in DEDUCTION_SPECS:
        defaults = {
            "include_active_employees": True,
            "is_pretax": spec["is_pretax"],
            "is_tax": spec["is_tax"],
            "is_condition_based": False,
            "is_fixed": spec["is_fixed"],
        }
        if spec["is_fixed"]:
            defaults["amount"] = float(spec["amount"])
            defaults["rate"] = 0.0
        else:
            defaults["rate"] = float(spec["rate"])
            defaults["based_on"] = spec["based_on"]
            defaults["amount"] = None
        deduction, status = upsert(
            Deduction,
            {"title": spec["title"], "company_id": company},
            defaults,
        )
        record(result, status, "Deduction", f"{deduction} @ {company}")
        items.append(deduction)
    return items


def _ensure_salary_structure(
    company: Company,
    allowances: list,
    deductions: list,
    result: SeederResult,
) -> SalaryStructure:
    structure, status = upsert(
        SalaryStructure,
        {"title": SALARY_STRUCTURE_TITLE, "company_id": company},
        {},
    )
    record(result, status, "Salary structure", structure)
    set_m2m(structure, "allowances", allowances)
    set_m2m(structure, "deductions", deductions)
    return structure


def _sync_contracts(
    employees: list[Employee],
    filing: FilingStatus,
    structure: SalaryStructure,
    result: SeederResult,
) -> None:
    for employee in employees:
        work_info = EmployeeWorkInformation.objects.filter(employee_id=employee).first()
        if work_info is None:
            continue
        contract = (
            Contract.objects.filter(employee_id=employee, contract_status="active")
            .order_by("pk")
            .first()
            or Contract.objects.filter(employee_id=employee).order_by("pk").first()
        )
        wage = float(work_info.basic_salary or 0)
        if wage <= 0:
            wage = 150_000.0
        joining = work_info.date_joining or timezone.localdate().replace(year=2020, month=1, day=1)
        end_date = work_info.contract_end_date
        if end_date is None or end_date <= timezone.localdate():
            end_date = timezone.localdate() + relativedelta(years=2)

        title = (
            f"{work_info.job_position_id} Contract"
            if work_info.job_position_id_id
            else f"{employee} Contract"
        )
        if contract is None:
            contract = Contract(
                employee_id=employee,
                contract_name=title[:250],
                contract_start_date=joining,
                contract_end_date=end_date,
                wage_type="monthly",
                pay_frequency="monthly",
                wage=wage,
                contract_status="active",
                filing_status=filing,
                department=work_info.department_id,
                job_position=work_info.job_position_id,
                job_role=work_info.job_role_id,
                shift=work_info.shift_id,
                work_type=work_info.work_type_id,
            )
            contract.save()
            contract.set_salary_structure(structure)
            record(result, "created", "Contract + structure", employee)
            continue

        updates = {
            "contract_name": title[:250],
            "contract_start_date": joining,
            "contract_end_date": end_date,
            "wage_type": "monthly",
            "pay_frequency": "monthly",
            "wage": wage,
            "contract_status": "active",
            "filing_status": filing,
            "department": work_info.department_id,
            "job_position": work_info.job_position_id,
            "job_role": work_info.job_role_id,
            "shift": work_info.shift_id,
            "work_type": work_info.work_type_id,
        }
        changed = False
        for field, value in updates.items():
            if getattr(contract, field) != value:
                setattr(contract, field, value)
                changed = True
        if changed:
            contract.save()
            record(result, "updated", "Contract", employee)
        if contract.salary_structure_id_id != structure.pk:
            contract.set_salary_structure(structure)
            record(result, "updated", "Contract salary structure", employee)


def _month_bounds(months_ago: int, today: date) -> tuple[date, date]:
    anchor = today.replace(day=1)
    start = anchor - relativedelta(months=months_ago)
    end = (start + relativedelta(months=1)) - timedelta(days=1)
    return start, end


def _seed_payslips(employees: list[Employee], result: SeederResult) -> None:
    today = timezone.localdate()
    created = 0
    for months_ago in (1, 2, 3):
        period_start, period_end = _month_bounds(months_ago, today)
        status = "paid" if months_ago >= 2 else "confirmed"
        for employee in employees:
            contract = Contract.objects.filter(
                employee_id=employee, contract_status="active"
            ).first()
            if not contract or period_end < contract.contract_start_date:
                continue
            start_date = max(period_start, contract.contract_start_date)
            if Payslip.objects.filter(
                employee_id=employee,
                start_date=period_start,
                end_date=period_end,
            ).exists():
                continue
            payslip_data = payroll_calculation(employee, start_date, period_end)
            if not payslip_data:
                continue
            data = {
                "employee": employee,
                "start_date": payslip_data["start_date"],
                "end_date": payslip_data["end_date"],
                "status": status,
                "contract_wage": payslip_data["contract_wage"],
                "basic_pay": payslip_data["basic_pay"],
                "gross_pay": payslip_data["gross_pay"],
                "deduction": payslip_data["total_deductions"],
                "net_pay": payslip_data["net_pay"],
                "pay_data": json.loads(payslip_data["json_data"]),
                "installments": payslip_data["installments"],
            }
            calculate_employer_contribution(data)
            instance = save_payslip(**data)
            record(result, "created", "Payslip", instance)
            created += 1
    record(
        result,
        "created",
        "Payslip batch",
        f"{created} payslips for last 3 complete months (PKR)",
    )


def _seed_reimbursements(result: SeederResult) -> None:
    # Reimbursement.save() requires request.user and an attachment for type
    # "reimbursement", so these are not created in CLI seeders.
    record(
        result,
        "existing",
        "Reimbursements",
        "skipped in seeder (create via UI with attachment)",
    )


def _seed_loans(result: SeederResult) -> None:
    today = timezone.localdate()
    for spec in LOAN_SPECS:
        employee = _employee_by_email(spec["email"])
        if employee is None:
            continue
        if LoanAccount.objects.filter(
            employee_id=employee, title=spec["title"]
        ).exists():
            record(result, "existing", "Loan", spec["title"])
            continue
        start = today.replace(day=1) + relativedelta(months=1)
        loan = LoanAccount(
            title=spec["title"],
            employee_id=employee,
            type="advanced_salary",
            loan_amount=float(spec["loan_amount"]),
            provided_date=today - timedelta(days=10),
            description="Seeded salary advance with monthly installments.",
            installments=int(spec["installments"]),
            installment_amount=float(spec["installment_amount"]),
            installment_start_date=start,
        )
        loan.save()
        record(result, "created", "Loan / advance", loan)


def _seed_company_payroll(company: Company, result: SeederResult) -> None:
    _ensure_payroll_settings(company, result)
    filing = _ensure_filing_and_tax(company, result)
    allowances = _ensure_allowances(company, result)
    deductions = _ensure_deductions(company, result)
    structure = _ensure_salary_structure(company, allowances, deductions, result)
    employees = _employees([company])
    _sync_contracts(employees, filing, structure, result)


@transaction.atomic
def seed() -> SeederResult:
    result = SeederResult()
    companies = _dsg_companies()
    if not companies:
        result.add(
            "existing",
            "Payroll seed skipped — run pakistan_org seeder first.",
        )
        return result

    _ensure_global_currency(result)
    _ensure_encashment_settings(result)
    for company in companies:
        _seed_company_payroll(company, result)

    all_employees = _employees(companies)
    _seed_payslips(all_employees, result)
    _seed_reimbursements(result)
    _seed_loans(result)

    result.add(
        "created",
        f"Payroll ready in {CURRENCY_SYMBOL} for {', '.join(DSG_COMPANY_NAMES)} "
        f"({len(all_employees)} employees).",
    )
    return result
