"""
Resolve which Company row drives login favicon, product name, and public branding.
"""

import re

from django.utils.encoding import force_str

from base.models import Company

# Created by seeders/organization_seeder.py — not meant as customer-facing brand.
SEED_PLACEHOLDER_COMPANY_NAME = "Default Company"

# Default product mark when a company has not uploaded its own icon.
DEFAULT_PRODUCT_LOGO = "images/ui/dsglogo.png"

_HORILLA_LABEL = re.compile(r"horilla", re.IGNORECASE)


def white_label_text(value):
    """
    Replace leftover Horilla product wording in user-facing labels.
    """
    if value is None:
        return value
    return _HORILLA_LABEL.sub("DSG", force_str(value))


def resolve_branding_company():
    """
    Pick the HQ company to show on login and other anonymous branding.

    Priority:
    1. HQ companies with an uploaded icon (prefer non-placeholder name)
    2. HQ companies without icon (prefer non-placeholder name)
    3. Newest HQ by primary key
    """
    hq_companies = list(Company.objects.filter(hq=True).order_by("-id"))
    if not hq_companies:
        return None

    def is_placeholder(company):
        return (company.company or "").strip() == SEED_PLACEHOLDER_COMPANY_NAME

    with_icon = [c for c in hq_companies if c.icon]
    for pool in (with_icon, hq_companies):
        if not pool:
            continue
        for company in pool:
            if not is_placeholder(company):
                return company
        return pool[0]

    return hq_companies[0]
