from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from seeders.registry import SEEDERS, get_seeders


class Command(BaseCommand):
    help = "Seed reusable master/reference data safely and idempotently."

    def add_arguments(self, parser):
        parser.add_argument(
            "--module",
            choices=list(SEEDERS.keys()),
            help="Run only one seeder module.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show seeding actions without committing database changes.",
        )

    def handle(self, *args, **options):
        module = options.get("module")
        dry_run = options["dry_run"]

        try:
            seeders = get_seeders(module)
        except ValueError as exc:
            raise CommandError(str(exc)) from exc

        self.stdout.write("Starting database seeding...")
        if dry_run:
            self.stdout.write(
                self.style.WARNING("Dry run enabled; changes will roll back.")
            )

        totals = {"created": 0, "updated": 0, "existing": 0}

        try:
            with transaction.atomic():
                for seeder in seeders:
                    self.stdout.write("")
                    self.stdout.write(self.style.MIGRATE_HEADING(f"[{seeder.slug}]"))

                    result = seeder.runner()
                    totals["created"] += result.created
                    totals["updated"] += result.updated
                    totals["existing"] += result.existing

                    for status, message in result.messages:
                        self._write_status(status, message)

                if dry_run:
                    transaction.set_rollback(True)
        except Exception as exc:
            raise CommandError(f"Database seeding failed: {exc}") from exc

        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS(
                "Database seeding completed successfully. "
                f"Created: {totals['created']}, "
                f"Updated: {totals['updated']}, "
                f"Already existing: {totals['existing']}."
            )
        )

    def _write_status(self, status, message):
        labels = {
            "created": ("Created", self.style.SUCCESS),
            "updated": ("Updated", self.style.WARNING),
            "existing": ("Already Exists", lambda value: value),
        }
        label, styler = labels.get(status, ("Info", lambda value: value))
        self.stdout.write(styler(f"{label}: {message}"))
