"""
Assets helpers for payslip PDF / HTML rendering.

wkhtmltopdf cannot reliably fetch localhost / media URLs from inside Docker,
so company logos are inlined as data URIs.
"""

from __future__ import annotations

import base64
import mimetypes
import os
from typing import Optional

from django.contrib.staticfiles import finders


DEFAULT_LOGO_STATIC = "images/ui/dsglogo.png"


def _file_to_data_uri(path: str) -> Optional[str]:
    if not path or not os.path.isfile(path):
        return None
    mime, _ = mimetypes.guess_type(path)
    if not mime:
        mime = "image/png"
    try:
        with open(path, "rb") as handle:
            encoded = base64.b64encode(handle.read()).decode("ascii")
        return f"data:{mime};base64,{encoded}"
    except OSError:
        return None


def resolve_company_logo_data_uri(company=None) -> Optional[str]:
    """
    Prefer the company's uploaded icon; otherwise fall back to the DSG static logo.
    Returns a data URI suitable for <img src="..."> in PDF HTML.
    """
    if company is not None:
        icon = getattr(company, "icon", None)
        if icon:
            try:
                path = icon.path
            except (NotImplementedError, ValueError, AttributeError):
                path = None
            data_uri = _file_to_data_uri(path) if path else None
            if data_uri:
                return data_uri

    static_path = finders.find(DEFAULT_LOGO_STATIC)
    if isinstance(static_path, (list, tuple)):
        static_path = static_path[0] if static_path else None
    return _file_to_data_uri(static_path)


def payslip_company_for_employee(employee, fallback_company=None):
    """Company to brand the payslip with."""
    work_info = getattr(employee, "employee_work_info", None)
    company = getattr(work_info, "company_id", None) if work_info else None
    return company or fallback_company
