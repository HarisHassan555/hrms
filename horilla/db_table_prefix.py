"""
Central rules for physical database table names (DSG HRMS).

When DB_TABLE_PREFIX is set (default: dsg_hr_), application tables are
prefixed at model load time so migrations and the ORM agree on names such as
dsg_hr_base_company instead of base_company.

HorillaModel subclasses are prefixed in HorillaModelBase at class creation.
Plain ``models.Model`` classes in HR apps are prefixed from HorillaConfig.ready().
"""

from django.apps import apps as django_apps
from django.conf import settings
from django.db import models

# Django contrib and packages that own their own table names.
EXCLUDED_APP_LABELS = frozenset(
    {
        "admin",
        "auth",
        "contenttypes",
        "sessions",
        "messages",
        "staticfiles",
        "sites",
        "notifications",
        "auditlog",
        "axes",
        "token_blacklist",
        "django_apscheduler",
        "rest_framework",
        "drf_yasg",
    }
)

# Never prefix tables that already use these names (framework / vendor).
EXCLUDED_TABLE_PREFIXES = (
    "django_",
    "auth_",
    "auditlog_",
    "axes_",
    "notifications_",
    "token_blacklist_",
    "django_apscheduler_",
)


def get_db_table_prefix() -> str:
    """Return the configured prefix, or empty string when prefixing is disabled."""
    return (getattr(settings, "DB_TABLE_PREFIX", None) or "").strip()


def is_excluded_table_name(table_name: str) -> bool:
    return any(table_name.startswith(prefix) for prefix in EXCLUDED_TABLE_PREFIXES)


def meta_class_defines_db_table(meta_class: type | None) -> bool:
    """True when this model class sets Meta.db_table directly (not inherited)."""
    return bool(meta_class and "db_table" in meta_class.__dict__)


def model_class_defines_db_table(model: type[models.Model]) -> bool:
    """True when this model class sets ``Meta.db_table`` on itself (not parents)."""
    return meta_class_defines_db_table(getattr(model, "Meta", None))


def resolve_prefixed_db_table(
    app_label: str,
    model_name: str,
    db_table: str,
    *,
    explicit_db_table: bool = False,
) -> str:
    """
    Compute the physical table name for a model, applying prefix rules once.

    Models with an explicit ``Meta.db_table`` (e.g. ``auth_user``) are never
    renamed. Default Django names ``{app_label}_{model_name}`` receive the prefix.
    """
    if explicit_db_table:
        return db_table

    prefix = get_db_table_prefix()
    if not prefix:
        return db_table
    if app_label in EXCLUDED_APP_LABELS:
        return db_table
    if db_table.startswith(prefix) or is_excluded_table_name(db_table):
        return db_table
    return f"{prefix}{db_table}"


def _set_migration_db_table(model: type[models.Model], table_name: str) -> None:
    """
    Set the ORM table name and the value Django migrations serialize.

    ``ModelState.from_model`` reads ``db_table`` from ``model._meta.original_attrs``,
    not from a runtime-only ``_meta.db_table`` mutation.
    """
    model._meta.db_table = table_name
    model._meta.original_attrs["db_table"] = table_name


def apply_db_table_prefix_to_model(
    model: type[models.Model],
    *,
    explicit_db_table: bool | None = None,
) -> None:
    """Apply prefix rules to model._meta and migration-visible Meta options."""
    meta = model._meta
    if meta.abstract or meta.proxy:
        return

    if explicit_db_table is None:
        explicit_db_table = model_class_defines_db_table(model)

    if explicit_db_table:
        return

    default_table = f"{meta.app_label}_{meta.model_name}"
    new_table = resolve_prefixed_db_table(
        meta.app_label,
        meta.model_name,
        meta.db_table,
        explicit_db_table=False,
    )
    if new_table != default_table:
        _set_migration_db_table(model, new_table)


_class_prepared_connected = False


def connect_class_prepared_signal() -> None:
    """
    Apply the prefix as each model class is registered.

    Must run before other apps' ``AppConfig.ready()`` hooks query the database;
    ``HorillaConfig`` is last in ``INSTALLED_APPS``, so a ready()-only hook is
    too late for startup queries (e.g. auth user, LDAP).
    """
    global _class_prepared_connected
    if _class_prepared_connected:
        return
    from django.db.models.signals import class_prepared

    class_prepared.connect(_on_class_prepared, dispatch_uid="horilla.db_table_prefix")
    _class_prepared_connected = True


def _on_class_prepared(sender, **kwargs):
    if not isinstance(sender, type):
        return
    try:
        if not issubclass(sender, models.Model):
            return
    except TypeError:
        return
    apply_db_table_prefix_to_model(sender)


def apply_db_table_prefix_to_plain_models() -> None:
    """Re-apply prefix rules after all models are registered (idempotent)."""
    if not get_db_table_prefix():
        return

    for model in django_apps.get_models():
        apply_db_table_prefix_to_model(model)
