"""
Platform operator (Data Sphere Global / SaaS owner) vs tenant company admins.

Tenant admins (e.g. Qarshi ``Admin`` group) keep HR module access but must not
see platform-level Settings entries (roles, all companies, LDAP, backups, …).
"""

from django.conf import settings


def _normalise_emails() -> set[str]:
    raw = getattr(settings, "PLATFORM_SUPERUSER_EMAILS", []) or []
    return {str(e).strip().lower() for e in raw if str(e).strip()}


def is_platform_superuser(user) -> bool:
    """
    Full platform operator: Django superuser and/or explicit allow-list email.
    """
    if not user or not getattr(user, "is_authenticated", False):
        return False
    if getattr(user, "is_superuser", False):
        return True
    email = (getattr(user, "email", None) or "").strip().lower()
    username = (getattr(user, "username", None) or "").strip().lower()
    allow = _normalise_emails()
    return bool(allow and (email in allow or username in allow))


def platform_settings_accessibility(request, submenu, user_perms, *args, **kwargs):
    """Settings items that only the platform operator may see."""
    return is_platform_superuser(request.user)


def platform_or_permission(permission_codename: str):
    """Platform operator always; otherwise require a single Django permission."""

    def _check(request, submenu, user_perms, *args, **kwargs):
        if is_platform_superuser(request.user):
            return True
        return request.user.has_perm(permission_codename)

    return _check


def platform_or_any_permission(*permission_codenames):
    """Platform operator always; otherwise any of the listed permissions."""

    def _check(request, submenu, user_perms, *args, **kwargs):
        if is_platform_superuser(request.user):
            return True
        return any(request.user.has_perm(p) for p in permission_codenames)

    return _check
