"""
Forms for handling payroll-related operations.

This module provides Django ModelForms for creating and managing payroll-related data,
including filing status, tax brackets, and federal tax records.

The forms in this module inherit from the Django `forms.ModelForm` class and customize
the widget attributes to enhance the user interface and provide a better user experience.

"""

from django import forms
from django.utils.translation import gettext_lazy as _

from base.forms import ModelForm
from payroll.models.models import FilingStatus
from payroll.models.tax_models import TaxBracket


class FilingStatusForm(ModelForm):
    """Minimal form for renaming a filing-status group."""

    cols = {
        "filing_status": 12,
    }

    class Meta:
        """Meta options for the form."""

        model = FilingStatus
        fields = ["filing_status"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["filing_status"].label = _("Name")


class TaxBracketForm(ModelForm):
    """Simple tax-slab form: range, rate, and fixed amount only."""

    cols = {
        "min_income": 6,
        "max_income": 6,
        "tax_rate": 6,
        "fixed_amount": 6,
    }

    class Meta:
        """Meta options for the form."""

        model = TaxBracket
        fields = [
            "min_income",
            "max_income",
            "tax_rate",
            "fixed_amount",
            "filing_status_id",
        ]
        widgets = {
            "filing_status_id": forms.HiddenInput(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["min_income"].label = _("Income Exceeds")
        self.fields["max_income"].label = _("Does Not Exceed")
        self.fields["tax_rate"].label = _("Tax Rate (%)")
        self.fields["fixed_amount"].label = _("Fixed Amount")
        self.fields["fixed_amount"].required = False
        if self.fields["fixed_amount"].initial is None:
            self.fields["fixed_amount"].initial = 0
        # Keep filing status out of the visible form.
        if "filing_status_id" in self.fields:
            self.fields["filing_status_id"].widget = forms.HiddenInput()
