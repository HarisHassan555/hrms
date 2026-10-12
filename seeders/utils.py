from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class SeederResult:
    created: int = 0
    updated: int = 0
    existing: int = 0
    messages: list[tuple[str, str]] = field(default_factory=list)

    def add(self, status: str, message: str) -> None:
        if status == "created":
            self.created += 1
        elif status == "updated":
            self.updated += 1
        else:
            self.existing += 1
        self.messages.append((status, message))

    def extend(self, other: "SeederResult") -> None:
        self.created += other.created
        self.updated += other.updated
        self.existing += other.existing
        self.messages.extend(other.messages)


def _normalise(value: Any) -> Any:
    if hasattr(value, "pk"):
        return value.pk
    return value


def values_changed(obj: object, values: dict[str, Any]) -> bool:
    for field_name, value in values.items():
        if _normalise(getattr(obj, field_name)) != _normalise(value):
            return True
    return False


def upsert(model, lookup: dict[str, Any], defaults: dict[str, Any] | None = None):
    """Update the first matching row, or create one when none exists.

    Some Horilla master tables rely on form-level uniqueness rather than a
    database constraint. Django's update_or_create would raise
    MultipleObjectsReturned if old production data already has duplicates, so
    this helper updates the first matching record and never creates an extra
    duplicate in that situation.
    """

    defaults = defaults or {}
    qs = model.objects.filter(**lookup).order_by("pk")
    obj = qs.first()
    created = obj is None
    changed = False

    if created:
        obj = model(**lookup, **defaults)
        obj.save()
        return obj, "created"

    if values_changed(obj, defaults):
        for field_name, value in defaults.items():
            setattr(obj, field_name, value)
        obj.save()
        changed = True

    return obj, "updated" if changed else "existing"


def set_m2m(obj: object, field_name: str, values: list[object] | tuple[object, ...]):
    manager = getattr(obj, field_name)
    old_ids = set(manager.values_list("pk", flat=True))
    new_ids = {value.pk for value in values}
    if old_ids != new_ids:
        manager.set(values)
        return "updated"
    return "existing"


def record(result: SeederResult, status: str, label: str, obj: object) -> None:
    result.add(status, f"{label} - {obj}")

