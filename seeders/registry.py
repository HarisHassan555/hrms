from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass
from typing import Callable

from . import admin_team_seeder, asset_seeder, attendance_seeder, employee_seeder, leave_seeder
from . import organization_seeder, qarshi_seeder
from .utils import SeederResult


SeederCallable = Callable[[], SeederResult]


@dataclass(frozen=True)
class Seeder:
    slug: str
    label: str
    runner: SeederCallable


SEEDERS = OrderedDict(
    (
        (
            "organization",
            Seeder("organization", "Organization", organization_seeder.seed),
        ),
        ("employee", Seeder("employee", "Employee", employee_seeder.seed)),
        ("attendance", Seeder("attendance", "Attendance", attendance_seeder.seed)),
        ("leave", Seeder("leave", "Leave", leave_seeder.seed)),
        ("asset", Seeder("asset", "Asset", asset_seeder.seed)),
        (
            "qarshi",
            Seeder(
                "qarshi",
                "Qarshi Industries (company + 4 users)",
                qarshi_seeder.seed,
            ),
        ),
        (
            "admin_team",
            Seeder(
                "admin_team",
                "20 Admin employees + org, shifts, leave master data",
                admin_team_seeder.seed,
            ),
        ),
    )
)


def get_seeders(module: str | None = None) -> list[Seeder]:
    if module is None:
        return list(SEEDERS.values())
    try:
        return [SEEDERS[module]]
    except KeyError as exc:
        choices = ", ".join(SEEDERS.keys())
        raise ValueError(
            f"Unknown seed module '{module}'. Available modules: {choices}"
        ) from exc
