"""
tax_models.py

This module contains the models for the tax calculation of taxable income.
"""

import math

from django.core.exceptions import ValidationError
from django.db import models
from django.urls import reverse
from django.utils.text import format_lazy
from django.utils.translation import gettext_lazy as _

from base.horilla_company_manager import HorillaCompanyManager
from base.models import Company
from horilla.models import HorillaModel
from payroll.models.models import FilingStatus


class PayrollSettings(HorillaModel):
    """
    Payroll settings model
    """

    choices = [
        ("prefix", _("Prefix")),
        ("postfix", _("Suffix")),
    ]

    currency_symbol = models.CharField(null=True, default="$", max_length=5)
    position = models.CharField(
        max_length=15, null=True, choices=choices, default="postfix"
    )

    company_id = models.ForeignKey(Company, null=True, on_delete=models.PROTECT)
    objects = HorillaCompanyManager("company_id")

    class Meta:
        verbose_name = _("Payroll Settings")
        verbose_name_plural = _("Payroll Settings")

    def __str__(self):
        return f"Payroll Settings {self.currency_symbol}"


class TaxBracket(HorillaModel):
    """
    Tax bracket for slab-based income tax.

    Annual tax for income in this bracket:

        fixed_amount + (yearly_income - min_income) * tax_rate / 100

    ``min_income`` is the threshold income exceeds; ``max_income`` is the
    inclusive upper limit ("does not exceed"). Only the matching bracket
    applies — ``fixed_amount`` holds cumulative tax from lower slabs.
    """

    filing_status_id = models.ForeignKey(
        FilingStatus,
        on_delete=models.CASCADE,
        verbose_name=_("Filing status"),
    )
    min_income = models.FloatField(
        null=False,
        blank=False,
        verbose_name=_("Income Exceeds"),
        help_text=_("Lower threshold: tax is charged on income above this amount."),
    )
    max_income = models.FloatField(
        null=True,
        blank=True,
        verbose_name=_("Does Not Exceed"),
        help_text=_("Inclusive upper limit for this bracket. Leave blank for no upper limit."),
    )
    tax_rate = models.FloatField(
        null=False,
        blank=False,
        default=0.0,
        verbose_name=_("Tax Rate (%)"),
        help_text=_("Percentage applied to income above the lower threshold."),
    )
    fixed_amount = models.FloatField(
        null=False,
        blank=False,
        default=0.0,
        verbose_name=_("Fixed Amount"),
        help_text=_(
            "Fixed tax added for this bracket (usually cumulative tax from lower slabs)."
        ),
    )
    objects = models.Manager()

    def __str__(self):
        fixed = self.fixed_amount or 0
        if self.max_income != math.inf:
            return (
                f"{self.filing_status_id}: {self.tax_rate}% + {fixed} "
                f"on ({self.min_income} – {self.max_income}]"
            )
        return (
            f"{self.filing_status_id}: {self.tax_rate}% + {fixed} "
            f"on income above {self.min_income}"
        )

    def get_display_max_income(self):
        """
        Retrieves the maximum income.
        Returns:
            float or None: The maximum income if it is a finite value, otherwise None.
        """
        if self.max_income != math.inf:
            return self.max_income
        return None

    def get_update_url(self):
        """
        Returns the URL for updating the tax bracket.
        """

        return reverse("tax-bracket-update", kwargs={"pk": self.pk})

    def get_delete_url(self):
        """
        Returns the URL for updating the tax bracket.
        """

        return reverse("tax-bracket-delete", kwargs={"tax_bracket_id": self.pk})

    def calculate_annual_tax(self, yearly_income: float) -> float:
        """
        Tax for ``yearly_income`` when it falls in this bracket.
        """
        excess = max(0.0, float(yearly_income) - float(self.min_income))
        return float(self.fixed_amount or 0) + (float(self.tax_rate) / 100.0) * excess

    def contains_income(self, yearly_income: float) -> bool:
        """
        True when income exceeds ``min_income`` and does not exceed ``max_income``.
        """
        income = float(yearly_income)
        upper = self.max_income if self.max_income is not None else math.inf
        return income > float(self.min_income) and income <= float(upper)

    def clean(self):
        super().clean()

        existing_bracket = TaxBracket.objects.filter(
            filing_status_id=self.filing_status_id,
            min_income=self.min_income,
            max_income=self.max_income,
            tax_rate=self.tax_rate,
            fixed_amount=self.fixed_amount or 0,
        ).exclude(pk=self.pk)
        if existing_bracket.exists():
            raise ValidationError(_("This tax bracket already exists"))

        if self.max_income is None:
            self.max_income = math.inf

        if self.min_income >= self.max_income:
            raise ValidationError(
                {
                    "max_income": _(
                        "Does not exceed must be greater than the income-exceeds threshold."
                    )
                }
            )

        if self.fixed_amount is None:
            self.fixed_amount = 0.0
        if self.fixed_amount < 0:
            raise ValidationError(
                {"fixed_amount": _("Fixed amount cannot be negative.")}
            )

        # Adjacent brackets that touch at the boundary are allowed
        # (e.g. 0–600000 then 600000–1200000). Reject only true overlaps.
        existing_brackets = TaxBracket.objects.filter(
            filing_status_id=self.filing_status_id
        ).exclude(pk=self.pk)
        for other in existing_brackets:
            other_max = other.max_income if other.max_income is not None else math.inf
            overlaps = (
                self.min_income < other_max and other.min_income < self.max_income
            )
            if overlaps:
                raise ValidationError(
                    {
                        "min_income": format_lazy(
                            "This bracket overlaps with existing bracket: {}.",
                            other,
                        )
                    }
                )
