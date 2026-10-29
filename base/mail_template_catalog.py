"""
Canonical titles for reusable mail templates that are easy to tell apart in Settings.

Recruitment candidate portal: applicants track application status before hire.
Onboarding complete-profile portal: hired candidates complete employee profile data.
"""

RECRUITMENT_CANDIDATE_PORTAL_TEMPLATE_TITLE = (
    "[Recruitment] Candidate Portal — Login & Track Application"
)
ONBOARDING_COMPLETE_PROFILE_PORTAL_TEMPLATE_TITLE = (
    "[Onboarding] Complete Profile Portal — Login & Details"
)

# Relative template fragment for recruitment portal login (host comes from request).
RECRUITMENT_CANDIDATE_LOGIN_PATH = "/recruitment/candidate-login/"
_RECRUITMENT_LOGIN_HREF_TEMPLATE = (
    "{{ request.scheme }}://{{ request.get_host }}"
    f"{RECRUITMENT_CANDIDATE_LOGIN_PATH}"
)


def mail_request_base_url(request) -> str:
    """Base URL matching the current application host (localhost, LAN, etc.)."""
    from base.methods import get_public_site_origin

    return (get_public_site_origin(request) or "").rstrip("/")


def build_onboarding_portal_absolute_url(
    request, candidate, *, create=False, refresh=False
) -> str:
    """
    Full onboarding self-service URL for ``candidate``.

    When ``create`` is true, creates an OnboardingPortal row if missing.
    When ``refresh`` is true (requires an existing or newly created portal),
    rotates the token — same as onboarding "Send portal link".
    """
    import secrets

    from django.apps import apps
    from django.core.exceptions import ObjectDoesNotExist

    if not apps.ready or not apps.is_installed("onboarding"):
        return ""

    from onboarding.models import OnboardingPortal

    portal_row = None
    try:
        portal_row = candidate.onboarding_portal
    except ObjectDoesNotExist:
        portal_row = None

    token = None
    if portal_row is None:
        if not create:
            return ""
        token = secrets.token_hex(15)
        OnboardingPortal.objects.create(candidate_id=candidate, token=token)
        # Clear reverse OneToOne cache so get_onboarding_portal_path sees the new row.
        try:
            del candidate.onboarding_portal
        except AttributeError:
            pass
    else:
        token = portal_row.token
        if refresh:
            token = secrets.token_hex(15)
            portal_row.token = token
            portal_row.used = False
            portal_row.count = 0
            portal_row.profile = None
            portal_row.save(update_fields=["token", "used", "count", "profile"])

    base = mail_request_base_url(request)
    if not base:
        return f"/onboarding/user-creation/{token}"
    return f"{base}/onboarding/user-creation/{token}"


def build_candidate_mail_template_context(
    request, candidate, *, ensure_onboarding_portal=False
):
    """Context for rendering recruitment/onboarding candidate mail templates."""
    from base.methods import build_safe_template_request

    safe_request = build_safe_template_request(request)
    portal = build_onboarding_portal_absolute_url(
        request, candidate, create=ensure_onboarding_portal
    )
    display_mobile = (getattr(candidate, "mobile", None) or "").strip()
    if not display_mobile:
        phone = getattr(candidate, "phone", None)
        if callable(phone):
            display_mobile = (phone() or "").strip()
    employee = getattr(getattr(request, "user", None), "employee_get", None)
    return {
        "instance": candidate,
        "self": employee,
        "request": safe_request,
        "portal": portal,
        "onboarding_portal_url": portal,
        "candidate_mobile": display_mobile,
    }


def mail_body_needs_onboarding_portal(body: str) -> bool:
    if not body:
        return False
    lowered = body.lower()
    return (
        "onboarding portal" in lowered
        or "get_onboarding_portal_path" in lowered
        or "onboarding_portal_url" in lowered
        or "{{portal}}" in lowered.replace(" ", "")
        or "onboarding/user-creation" in lowered
        or ONBOARDING_COMPLETE_PROFILE_PORTAL_TEMPLATE_TITLE.lower() in lowered
    )


_LEGACY_RECRUITMENT_CANDIDATE_PORTAL_TITLES = (
    "Candidate Portal Login",
    "Candidate Self Tracking Portal Automation",
)


def _promote_legacy_title(canonical_title: str, legacy_titles: tuple[str, ...]) -> None:
    from base.models import HorillaMailTemplate

    if HorillaMailTemplate.objects.filter(title=canonical_title).exists():
        for legacy in legacy_titles:
            HorillaMailTemplate.objects.filter(title=legacy).delete()
        return

    for legacy in legacy_titles:
        legacy_row = HorillaMailTemplate.objects.filter(title=legacy).first()
        if legacy_row is None:
            continue
        legacy_row.title = canonical_title
        legacy_row.save(update_fields=["title"])
        for other in legacy_titles:
            if other != legacy:
                HorillaMailTemplate.objects.filter(title=other).delete()
        return


def recruitment_candidate_portal_template_body() -> str:
    return (
        '<div style="font-family: \'Segoe UI\', Arial, sans-serif; background-color: #f4f6f9; padding: 24px;">'
        '<div style="max-width: 640px; margin: auto; background: #ffffff; border-radius: 12px; padding: 28px; '
        'box-shadow: 0 4px 14px rgba(0,0,0,0.08); border: 1px solid #eceff3;">'
        '<h2 style="margin: 0 0 18px 0; color: #1f2937; font-size: 22px;">'
        "Recruitment candidate portal — login details"
        "</h2>"
        '<p style="font-size: 14px; color: #374151; line-height: 1.7; margin: 0 0 14px 0;">'
        "Hi {{instance.get_full_name}},</p>"
        '<p style="font-size: 14px; color: #374151; line-height: 1.7; margin: 0 0 16px 0;">'
        "Use the recruitment candidate portal to track your application status and stay updated "
        "during the hiring process.</p>"
        '<div style="margin: 18px 0; padding: 16px; background: #f9fafb; border-left: 4px solid #4f46e5; border-radius: 8px;">'
        '<p style="margin: 0 0 8px 0; font-size: 14px; color: #111827;">'
        "<strong>Portal link:</strong> "
        f'<a href="{_RECRUITMENT_LOGIN_HREF_TEMPLATE}" target="_blank" '
        'style="color: #4f46e5; text-decoration: none;">'
        f"{_RECRUITMENT_LOGIN_HREF_TEMPLATE}"
        "</a></p>"
        '<p style="margin: 0 0 8px 0; font-size: 14px; color: #111827;">'
        "<strong>Username (email):</strong> {{instance.email}}</p>"
        '<p style="margin: 0; font-size: 14px; color: #111827;">'
        "<strong>Password (mobile number):</strong> {{instance.mobile}}</p>"
        "</div>"
        '<p style="font-size: 13px; color: #6b7280; margin: 0 0 18px 0;">'
        "For security, please keep these credentials private.</p>"
        '<hr style="border: none; border-top: 1px solid #e5e7eb; margin: 20px 0;">'
        '<p style="font-size: 13px; color: #6b7280; margin: 0;">Regards,</p>'
        '<p style="font-size: 13px; color: #111827; margin: 6px 0 0 0;">'
        "<strong>{{self.get_full_name}} | {{self.get_department}} | {{self.get_company}}</strong></p>"
        "</div></div>"
    )


def onboarding_complete_profile_portal_template_body() -> str:
    """Match the recruitment candidate-portal mail layout (credentials callout + sign-off)."""
    return (
        '<div style="font-family: \'Segoe UI\', Arial, sans-serif; background-color: #f4f6f9; padding: 24px;">'
        '<div style="max-width: 640px; margin: auto; background: #ffffff; border-radius: 12px; padding: 28px; '
        'box-shadow: 0 4px 14px rgba(0,0,0,0.08); border: 1px solid #eceff3;">'
        '<h2 style="margin: 0 0 18px 0; color: #1f2937; font-size: 22px;">'
        "Onboarding Portal — Complete Profile Details"
        "</h2>"
        '<p style="font-size: 14px; color: #374151; line-height: 1.7; margin: 0 0 14px 0;">'
        "Hi {{instance.get_full_name}},</p>"
        '<p style="font-size: 14px; color: #374151; line-height: 1.7; margin: 0 0 16px 0;">'
        "Congratulations on your selection. Use the onboarding portal below to complete your "
        "employee profile, upload required documents, and finish onboarding tasks before you join "
        "<strong>{{instance.get_company}}</strong> as "
        "<strong>{{instance.get_job_position}}</strong>.</p>"
        '<div style="margin: 18px 0; padding: 16px; background: #f9fafb; border-left: 4px solid hsl(8, 77%, 56%); border-radius: 8px;">'
        '<p style="margin: 0 0 8px 0; font-size: 14px; color: #111827;">'
        "<strong>Portal link:</strong> "
        '<a href="{{ portal }}" target="_blank" '
        'style="color: hsl(8, 77%, 56%); text-decoration: none;">'
        "{{ portal }}</a></p>"
        '<p style="margin: 0 0 8px 0; font-size: 14px; color: #111827;">'
        "<strong>Email (for your account):</strong> {{instance.email}}</p>"
        '<p style="margin: 0 0 8px 0; font-size: 14px; color: #111827;">'
        "<strong>Mobile number:</strong> {{ candidate_mobile }}</p>"
        '<p style="margin: 0; font-size: 14px; color: #111827;">'
        "<strong>How to access:</strong> Open the personal link above. You will create your "
        "password on first visit — this is not the recruitment candidate portal.</p>"
        "</div>"
        '<p style="font-size: 13px; color: #6b7280; margin: 0 0 18px 0;">'
        "For security, please keep this onboarding link private and do not forward it.</p>"
        '<hr style="border: none; border-top: 1px solid #e5e7eb; margin: 20px 0;">'
        '<p style="font-size: 13px; color: #6b7280; margin: 0;">Regards,</p>'
        '<p style="font-size: 13px; color: #111827; margin: 6px 0 0 0;">'
        "<strong>{{self.get_full_name}} | {{self.get_department}} | {{self.get_company}}</strong></p>"
        "</div></div>"
    )


def _is_legacy_onboarding_portal_template_body(body: str) -> bool:
    if not body:
        return True
    # Canonical body uses the full absolute URL from mail context.
    if "{{ portal }}" not in body and "{{portal}}" not in body.replace(" ", ""):
        return True
    if "get_onboarding_portal_path" in body:
        return True
    if "{% else %}" in body:
        return True
    # Older seeds baked an absolute host into the body instead of {{ portal }}.
    if "localhost" in body.lower() and "{{ portal }}" not in body:
        return True
    return False


def _is_legacy_recruitment_portal_template_body(body: str) -> bool:
    if not body:
        return True
    if _RECRUITMENT_LOGIN_HREF_TEMPLATE not in body:
        return True
    # Absolute hosts from older migrations must be replaced with request-based tags.
    lowered = body.lower()
    if "localhost" in lowered or "192.168." in lowered:
        return True
    return False


def ensure_recruitment_candidate_portal_mail_template():
    from base.models import HorillaMailTemplate

    _promote_legacy_title(
        RECRUITMENT_CANDIDATE_PORTAL_TEMPLATE_TITLE,
        _LEGACY_RECRUITMENT_CANDIDATE_PORTAL_TITLES,
    )
    canonical = recruitment_candidate_portal_template_body()
    template, created = HorillaMailTemplate.objects.get_or_create(
        title=RECRUITMENT_CANDIDATE_PORTAL_TEMPLATE_TITLE,
        defaults={"body": canonical},
    )
    if not created and _is_legacy_recruitment_portal_template_body(template.body):
        template.body = canonical
        template.save(update_fields=["body"])
    return template


def ensure_onboarding_complete_profile_portal_mail_template():
    from base.models import HorillaMailTemplate

    canonical_body = onboarding_complete_profile_portal_template_body()
    template, created = HorillaMailTemplate.objects.get_or_create(
        title=ONBOARDING_COMPLETE_PROFILE_PORTAL_TEMPLATE_TITLE,
        defaults={"body": canonical_body},
    )
    if not created and _is_legacy_onboarding_portal_template_body(template.body):
        template.body = canonical_body
        template.save(update_fields=["body"])
    return template
