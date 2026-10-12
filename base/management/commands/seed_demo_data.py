import json

from django.core.management.base import BaseCommand, CommandError

from base.demo_data.registry import DEMO_SEED_MODULES, run_demo_seed_module


class Command(BaseCommand):
    help = "Seed demo data for one module, or all modules, without loading fixtures."

    def add_arguments(self, parser):
        choices = ["all", *[module.slug for module in DEMO_SEED_MODULES]]
        parser.add_argument(
            "--module",
            choices=choices,
            default="all",
            help="Demo data module to seed.",
        )

    def handle(self, *args, **options):
        module = options["module"]
        try:
            result = run_demo_seed_module(module)
        except Exception as exc:
            raise CommandError(f"Demo seeding failed for {module}: {exc}") from exc

        self.stdout.write(
            self.style.SUCCESS(f"Demo seeding completed for module: {module}")
        )
        self.stdout.write(json.dumps(result, default=str, indent=2))
