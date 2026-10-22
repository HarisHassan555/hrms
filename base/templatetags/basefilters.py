import json
import re

import bleach
from bleach.css_sanitizer import CSSSanitizer
from django import template
from django.core.paginator import Page, Paginator
from django.utils.safestring import mark_safe

from base.methods import get_pagination
from base.models import MultipleApprovalManagers
from employee.models import Employee, EmployeeWorkInformation
from horilla.menu.settings_menu import get_settings_menu

register = template.Library()

# Tags and attributes the rich-text editors in this app legitimately produce.
# Deliberately excludes script/style/iframe/object/embed and every event
# handler, so stored markup cannot execute.
_ALLOWED_HTML_TAGS = {
    # "img" is here because these fields are written in a rich-text editor and
    # people paste screenshots into them -- a helpdesk ticket whose screenshot
    # silently vanished on upgrade is a support problem, not a security win.
    # The src protocol allow-list below is what keeps it safe.
    "a",
    "article",
    "b",
    "blockquote",
    "br",
    "code",
    "col",
    "colgroup",
    "div",
    "em",
    "figure",
    "figcaption",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "header",
    "hr",
    "i",
    "img",
    "li",
    "ol",
    "p",
    "pre",
    "s",
    "section",
    "small",
    "span",
    "strong",
    "sub",
    "sup",
    "table",
    "tbody",
    "td",
    "tfoot",
    "th",
    "thead",
    "tr",
    "u",
    "ul",
}
_ALLOWED_HTML_ATTRS = {
    "a": ["href", "title", "target", "rel"],
    "img": ["src", "alt", "title", "width", "height"],
    "td": ["colspan", "rowspan", "width", "height"],
    "th": ["colspan", "rowspan", "width", "height"],
    "table": ["width", "border", "cellpadding", "cellspacing"],
    "col": ["width", "span"],
    "colgroup": ["span"],
    # "style" so that colour and layout applied in the editor survive.
    "*": ["class", "style", "align", "valign"],
}

# Layout and typography the policy / Summernote editors actually emit.
# Dangerous properties (position, behaviour, etc.) stay off this list.
_ALLOWED_CSS_PROPERTIES = [
    "color",
    "background",
    "background-color",
    "font-size",
    "font-weight",
    "font-style",
    "font-family",
    "text-align",
    "text-decoration",
    "text-transform",
    "line-height",
    "letter-spacing",
    "white-space",
    "vertical-align",
    "display",
    "flex",
    "flex-direction",
    "flex-wrap",
    "flex-grow",
    "flex-shrink",
    "flex-basis",
    "align-items",
    "align-content",
    "align-self",
    "justify-content",
    "justify-items",
    "justify-self",
    "gap",
    "row-gap",
    "column-gap",
    "grid-template-columns",
    "grid-template-rows",
    "grid-column",
    "grid-row",
    "width",
    "min-width",
    "max-width",
    "height",
    "min-height",
    "max-height",
    "margin",
    "margin-top",
    "margin-right",
    "margin-bottom",
    "margin-left",
    "padding",
    "padding-top",
    "padding-right",
    "padding-bottom",
    "padding-left",
    "border",
    "border-top",
    "border-right",
    "border-bottom",
    "border-left",
    "border-width",
    "border-style",
    "border-color",
    "border-radius",
    "border-collapse",
    "border-spacing",
    "box-sizing",
    "box-shadow",
    "opacity",
    "overflow",
    "overflow-x",
    "overflow-y",
    "list-style",
    "list-style-type",
    "list-style-position",
    "object-fit",
    "float",
    "clear",
]


class _StrictCSSSanitizer(CSSSanitizer):
    """Allow layout CSS while still blocking executable values.

    bleach validates the property NAME against the allow-list but does not
    look at the VALUE, so `color: expression(alert(1))` or `background:url(...)`
    would otherwise pass. Safe colour/layout functions (rgb, calc, …) are
    kept so designed policy HTML still renders.
    """

    _BLOCKED_FUNCTION = re.compile(
        r"(?:url|expression|image-set|element|attr)\s*\(",
        re.IGNORECASE,
    )

    def sanitize_css(self, style):
        declarations = []
        for declaration in super().sanitize_css(style).split(";"):
            if not declaration.strip():
                continue
            _, _, value = declaration.partition(":")
            lowered = value.lower()
            if self._BLOCKED_FUNCTION.search(value) or "javascript:" in lowered:
                continue
            declarations.append(declaration.strip())
        return "; ".join(declarations) + (";" if declarations else "")


_CSS_SANITIZER = _StrictCSSSanitizer(allowed_css_properties=_ALLOWED_CSS_PROPERTIES)

_STYLE_BLOCK_RE = re.compile(
    r"<\s*style\b[^>]*>(.*?)</\s*style\s*>",
    re.IGNORECASE | re.DOTALL,
)
_DEFAULT_RICHTEXT_SCOPE = ".oh-richtext"


def _scope_css_selector(selector, scope):
    parts = []
    for part in selector.split(","):
        part = part.strip()
        if not part or "</" in part or ";" in part:
            continue
        lowered = part.lower()
        if lowered in {"html", "body", ":root"}:
            parts.append(scope)
        elif part.startswith(scope):
            parts.append(part)
        else:
            parts.append(f"{scope} {part}")
    return ", ".join(parts)


def _sanitize_style_block(css, scope=_DEFAULT_RICHTEXT_SCOPE):
    """Keep editor <style> rules, scoped so they cannot restyle the app chrome."""
    css = re.sub(r"/\*.*?\*/", "", css or "", flags=re.DOTALL)
    css = re.sub(r"@import[^;]*;", "", css, flags=re.IGNORECASE)
    rules = []
    i = 0
    length = len(css)
    while i < length:
        while i < length and css[i].isspace():
            i += 1
        if i >= length:
            break
        if css[i] == "@":
            j = i
            while j < length and css[j] not in "{;":
                j += 1
            if j < length and css[j] == ";":
                i = j + 1
                continue
            if j < length and css[j] == "{":
                depth = 1
                j += 1
                while j < length and depth:
                    if css[j] == "{":
                        depth += 1
                    elif css[j] == "}":
                        depth -= 1
                    j += 1
                i = j
                continue
            break
        brace = css.find("{", i)
        end = css.find("}", i)
        if brace == -1 or end == -1 or end < brace:
            break
        selector = css[i:brace].strip()
        declarations = _CSS_SANITIZER.sanitize_css(css[brace + 1 : end])
        i = end + 1
        if not selector or not declarations:
            continue
        scoped = _scope_css_selector(selector, scope)
        if scoped:
            rules.append(f"{scoped} {{ {declarations} }}")
    return "\n".join(rules)


@register.filter(name="sanitize_html")
def sanitize_html(value, scope=_DEFAULT_RICHTEXT_SCOPE):
    """
    Render user-authored rich text without trusting it.

    These fields (ticket descriptions and comments, recruitment
    descriptions, policy bodies, OKR comments) were previously rendered
    with ``|safe``. The only thing standing between a user and stored XSS
    was the ``has_xss`` regex applied at write time, which is a blocklist
    and not a parser -- anything it fails to match became executable HTML
    in every viewer's session. This strips to an allow-list instead, so a
    gap in that regex is no longer exploitable.

    ``<style>`` blocks from the editor are kept after CSS sanitizing and
    scoped under ``scope`` (default ``.oh-richtext``) so designed policy
    layouts survive without restyling the rest of the app.
    """
    if not value:
        return ""
    raw = str(value)
    scoped_css = []

    def _remember_style(match):
        cleaned = _sanitize_style_block(match.group(1), scope)
        if cleaned:
            scoped_css.append(cleaned)
        return ""

    html = _STYLE_BLOCK_RE.sub(_remember_style, raw)
    cleaned = bleach.clean(
        html,
        tags=_ALLOWED_HTML_TAGS,
        attributes=_ALLOWED_HTML_ATTRS,
        # No "data": a data: URI on an <img> can carry text/html, which is
        # a script delivery vector. Pasted screenshots that were inlined as
        # base64 are dropped; hosted ones survive.
        protocols=["http", "https", "mailto"],
        css_sanitizer=_CSS_SANITIZER,
        strip=True,
    )
    if scoped_css:
        cleaned = "<style>" + "\n".join(scoped_css) + "</style>" + cleaned
    return mark_safe(cleaned)


@register.filter
def equals(value, arg):
    """Check if value equals arg"""
    return value == arg


def _get_employee_of_user(user):
    """
    Resolve the Employee for a user once per request and cache it on the
    user object - this tag/filter is called once per row in list views, and
    without this cache each call re-issues the same lookup query.
    """
    if not hasattr(user, "_horilla_employee_cache"):
        user._horilla_employee_cache = Employee.objects.filter(
            employee_user_id=user
        ).first()
    return user._horilla_employee_cache


@register.simple_tag
def is_manager_of(user, instance, field_name="employee_id"):
    employee = _get_employee_of_user(user)

    target_employee = getattr(instance, field_name, None)

    if not hasattr(user, "_horilla_is_manager_of_cache"):
        user._horilla_is_manager_of_cache = {}
    cache = user._horilla_is_manager_of_cache
    key = (getattr(employee, "id", None), getattr(target_employee, "id", None))
    if key not in cache:
        cache[key] = EmployeeWorkInformation.objects.filter(
            reporting_manager_id=employee, employee_id=target_employee
        ).exists()
    return cache[key]


@register.filter(name="is_reportingmanager")
def is_reportingmanager(user):
    """

    This method will return true if the user employee profile is reporting manager to any employee
    """
    employee = _get_employee_of_user(user)
    return EmployeeWorkInformation.objects.filter(
        reporting_manager_id=employee
    ).exists()


@register.filter(name="is_leave_approval_manager")
def is_leave_approval_manager(user):
    """
    This method will return true if the user is comes in MultipleApprovalCondition model as approving manager
    """
    if hasattr(user, "_horilla_is_leave_approval_manager_cache"):
        return user._horilla_is_leave_approval_manager_cache
    employee = _get_employee_of_user(user)
    manager = (
        MultipleApprovalManagers.objects.entire()
        .filter(employee_id=employee.id)
        .exists()
        if employee
        else False
    )
    user._horilla_is_leave_approval_manager_cache = manager
    return manager


@register.filter(name="check_manager")
def check_manager(user, instance):
    try:
        if isinstance(instance, Employee):
            return instance.employee_work_info.reporting_manager_id == user.employee_get
        return (
            user.employee_get
            == instance.employee_id.employee_work_info.reporting_manager_id
        )
    except:
        return False


@register.filter(name="filtersubordinates")
def filtersubordinates(user):
    """
    This method returns true if the user employee has corresponding related reporting manager object in EmployeeWorkInformation model
    args:
        user    : request.user
    """

    employee = user.employee_get
    employee_manages = employee.reporting_manager.all()
    return employee_manages.exists()


@register.filter(name="filter_field")
def filter_field(value):
    if value.endswith("_id"):
        value = value[:-3]
    if value.endswith("_ids"):
        value = value[:-4]
    splitted = value.split("__")

    return splitted[-1].replace("_", " ").capitalize()


@register.filter(name="user_perms")
def user_perms(perms):
    """
    permission names return method
    """
    return json.dumps(list(perms.values_list("codename", flat="True")))


@register.filter(name="all_user_perms")
def all_user_perms(user):
    """
    Return JSON list of effective permission codenames for a user for the
    currently selected company (group assignments + direct user permissions).
    """
    if not user:
        return json.dumps([])
    from base.auth_backends import get_effective_permission_codenames

    return json.dumps(get_effective_permission_codenames(user))


@register.filter(name="company_user_groups")
def company_user_groups(user):
    """
    Groups assigned to the user in the currently selected company.
    """
    from base.auth_backends import get_user_groups_for_company

    if not user:
        return []
    return list(get_user_groups_for_company(user))


@register.filter(name="abs_value")
def abs_value(value):
    """
    permission names return method
    """
    return abs(value)


@register.filter(name="startswith")
def startswith(value, arg):
    """Checks if the value starts with the provided argument."""
    return value.startswith(arg)


@register.filter(name="has_content")
def has_content(value):
    """Returns True if the input string has non-whitespace content."""
    if isinstance(value, str):
        return bool(value.strip())
    return True


@register.filter(name="unique_breadcrumbs")
def unique_breadcrumbs(breadcrumbs):
    """Drop later breadcrumbs that share a name with an earlier one."""
    seen = set()
    unique = []
    for crumb in breadcrumbs:
        name = crumb.get("name")
        if name not in seen:
            seen.add(name)
            unique.append(crumb)
    return unique


@register.filter(name="readable")
def readable(value):
    try:
        value = value.replace("_", " ").replace("id", "").title()
    except:
        value = value
    return value


@register.simple_tag(takes_context=True)
def general_section_main(context):
    user = context["request"].user

    if not user.is_authenticated:
        return False

    return any(
        [
            user.has_perm("base.change_announcementexpire"),
            user.has_perm("base.view_dynamicpagination"),
            user.has_perm("horilla_audit.view_accountblockunblock"),
            user.has_perm("offboarding.change_offboardinggeneralsetting"),
            user.has_perm("attendance.change_attendancegeneralsetting"),
            user.has_perm("payroll.change_payrollgeneralsetting"),
            user.has_perm("employee.change_employeegeneralsetting"),
            user.has_perm("payroll.change_encashmentgeneralsettings"),
            user.has_perm("horilla_audit.view_historytrackingfields"),
            user.has_perm("payroll.view_payrollsettings"),
            user.has_perm("auth.view_permission"),
            user.has_perm("auth.view_group"),
            user.has_perm("base.view_company"),
            user.has_perm("base.view_tags"),
            user.has_perm("employee.view_employeetag"),
            user.has_perm("horilla_audit.view_audittag"),
            user.has_perm("base.view_dynamicemailconfiguration"),
            user.has_perm("horilla_backup.view_googledrivebackup"),
        ]
    )


@register.simple_tag(takes_context=True)
def general_section(context):
    user = context["request"].user

    if not user.is_authenticated:
        return False

    return any(
        [
            user.has_perm("base.change_announcementexpire"),
            user.has_perm("base.view_dynamicpagination"),
            user.has_perm("horilla_audit.view_accountblockunblock"),
            user.has_perm("offboarding.change_offboardinggeneralsetting"),
            user.has_perm("attendance.change_attendancegeneralsetting"),
            user.has_perm("payroll.change_payrollgeneralsetting"),
            user.has_perm("employee.change_employeegeneralsetting"),
            user.has_perm("payroll.change_encashmentgeneralsettings"),
            user.has_perm("horilla_audit.view_historytrackingfields"),
            user.has_perm("payroll.view_payrollsettings"),
        ]
    )


@register.simple_tag(takes_context=True)
def employee_section(context):
    user = context["request"].user

    if not user.is_authenticated:
        return False

    return any(
        [
            user.has_perm("base.view_worktype"),
            user.has_perm("base.view_rotatingworktype"),
            user.has_perm("base.view_employeeshift"),
            user.has_perm("base.view_rotatingshift"),
            user.has_perm("base.view_employeeshiftschedule"),
            user.has_perm("base.view_employeetype"),
            user.has_perm("employee.view_actiontype"),
            user.has_perm("employee.view_employeetag"),
        ]
    )


@register.simple_tag(takes_context=True)
def attendance_section(context):
    user = context["request"].user

    if not user.is_authenticated:
        return False

    return any(
        [
            user.has_perm("attendance.view_attendancevalidationcondition"),
            user.has_perm("base.view_biometricattendance"),
            user.has_perm("attendance.add_attendance"),
            user.has_perm("geofencing.add_geofencing"),
            user.has_perm("facedetection.add_facedetection"),
        ]
    )


@register.simple_tag(takes_context=True)
def show_section(context):
    user = context["request"].user

    if not user.is_authenticated:
        return False

    request = context.get("request")
    if request is not None:
        from horilla.menu.settings_menu import get_settings_menu

        if any(section.get("items") for section in get_settings_menu(request)):
            return True

    return any(
        [
            user.has_perm("attendance.view_attendancevalidationcondition"),
            user.has_perm("helpdesk.view_departmentmanager"),
            user.has_perm("helpdesk.view_tickettype"),
            user.has_perm("employee.view_employeetag"),
            user.has_perm("pms.add_bonuspointsetting"),
            user.has_perm("payroll.view_payslipautogenerate"),
            user.has_perm("leave.add_restrictleave"),
            user.has_perm("base.view_biometricattendance"),
            user.has_perm("attendance.add_attendance"),
            user.has_perm("geofencing.add_geofencing"),
            user.has_perm("facedetection.add_facedetection"),
            user.has_perm("recruitment.view_rejectreason"),
            user.has_perm("recruitment.add_linkedinaccount"),
            user.has_perm("horilla_audit.view_accountblockunblock"),
            user.has_perm("offboarding.change_offboardinggeneralsetting"),
            user.has_perm("attendance.change_attendancegeneralsetting"),
            user.has_perm("payroll.change_payrollgeneralsetting"),
            user.has_perm("employee.change_employeegeneralsetting"),
            user.has_perm("payroll.change_encashmentgeneralsettings"),
            user.has_perm("payroll.view_payrollsettings"),
            user.has_perm("auth.view_permission"),
            user.has_perm("auth.view_group"),
            user.has_perm("horilla_audit.view_audittag"),
            user.has_perm("horilla_backup.view_googledrivebackup"),
            user.has_perm("horilla_ldap.add_ldapsettings"),
            user.has_perm("horilla_ldap.update_ldapsettings"),
            user.has_perm("employee.view_actiontype"),
            user.has_perm("base.view_tags"),
            user.has_perm("whatsapp.view_whatsappcredientials"),
            user.has_perm("base.view_company"),
            user.has_perm("base.view_tags"),
            user.has_perm("base.view_dynamicemailconfiguration"),
            user.has_perm("base.view_department"),
            user.has_perm("base.view_jobposition"),
            user.has_perm("base.view_jobrole"),
            user.has_perm("base.view_worktype"),
            user.has_perm("base.view_rotatingworktype"),
            user.has_perm("base.view_employeeshift"),
            user.has_perm("base.view_rotatingshift"),
            user.has_perm("base.view_employeeshiftschedule"),
            user.has_perm("base.view_employeetype"),
            user.has_perm("base.change_announcementexpire"),
            user.has_perm("base.view_dynamicpagination"),
            user.has_perm("horilla_backup.view_googledrivebackup"),
            user.has_perm("recruitment.view_linkedinaccount"),
            user.has_perm("horilla_ldap.add_ldapsettings"),
            user.has_perm("horilla_ldap.update_ldapsettings"),
            user.has_perm("horilla_meet.view_googlecloudcredential"),
            user.has_perm("whatsapp.add_whatsappcredientials"),
            user.has_perm("horilla_theme.view_horillacolortheme"),
        ]
    )


@register.simple_tag(takes_context=True)
def settings_menu(context):

    request = context.get("request")
    if request is None:
        return []
    return get_settings_menu(request)


@register.simple_tag
def settings_search_index():
    """
    Build the settings search index dynamically from the settings_registry.

    Each item in a sidebar class can declare a ``search_entries`` list of
    ``{"text": ..., "description": ...}`` dicts for field-level search
    granularity.  Items without ``search_entries`` fall back to a single
    page-level entry using the item label.

    To add new searchable fields for a settings page, open the relevant
    ``<app>/sidebar.py``, find the item dict, and add/extend its
    ``search_entries`` list — no changes needed anywhere else.
    """
    import json

    from horilla.menu.settings_menu import settings_registry

    entries = []
    seen = set()  # (text_lower, url) pairs — prevents exact duplicates

    for cls in settings_registry._entries:
        obj = cls()
        section = str(getattr(obj, "title", ""))
        for item in getattr(obj, "items", []):
            page = str(item.get("label", ""))
            try:
                url = str(item.get("url", ""))
            except Exception:
                continue
            if not page or not url:
                continue

            search_entries = item.get("search_entries", [])
            if search_entries:
                for entry in search_entries:
                    text = str(entry.get("text", ""))
                    description = str(entry.get("description", ""))
                    key = (text.lower(), url)
                    if not text or key in seen:
                        continue
                    seen.add(key)
                    anchor = str(entry.get("anchor", ""))
                    entries.append(
                        {
                            "text": text,
                            "description": description,
                            "section": section,
                            "page": page,
                            "url": f"{url}#{anchor}" if anchor else url,
                        }
                    )
            else:
                # Fallback: page label only (no field-level granularity yet)
                key = (page.lower(), url)
                if key not in seen:
                    seen.add(key)
                    entries.append(
                        {
                            "text": page,
                            "description": "",
                            "section": section,
                            "page": page,
                            "url": url,
                        }
                    )

    return json.dumps(entries, ensure_ascii=False)


@register.filter(name="config_perms")
def config_perms(user):
    from django.apps import apps

    app_permissions = {
        "leave": ["leave.view_restrictleave"],
        "base": [
            "base.add_holidays",
            "base.change_holidays",
            "base.add_companyleaves",
            "base.change_companyleaves",
            "base.add_horillamailtemplates",
            "base.view_horillamailtemplates",
        ],
    }
    for app, perms in app_permissions.items():
        if apps.is_installed(app):
            for perm in perms:
                if user.has_perm(perm):
                    return True
    return False
