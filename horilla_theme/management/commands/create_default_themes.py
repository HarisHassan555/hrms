from django.core.management.base import BaseCommand

from horilla_theme.models import THEMES_DATA, HorillaColorTheme

# Legacy default theme name used before DSG indigo branding.
_LEGACY_DEFAULT_NAMES = ("Coral Red Theme (Default)",)


class Command(BaseCommand):
    help = "Create or sync default color themes for DSG HRMS"

    def add_arguments(self, parser):
        parser.add_argument(
            "--sync",
            action="store_true",
            help="Update existing theme rows to match THEMES_DATA (and migrate legacy default).",
        )

    def handle(self, *args, **options):
        sync = options["sync"]
        if HorillaColorTheme.objects.exists() and not sync:
            self.stdout.write(
                self.style.WARNING(
                    "Themes already exist. Re-run with --sync to update them."
                )
            )
            return

        created_count = 0
        updated_count = 0
        self.stdout.write("Syncing default color themes..." if sync else "Creating default color themes...")

        for theme_data in THEMES_DATA:
            name = theme_data["name"]
            fields = {k: v for k, v in theme_data.items() if k != "name"}
            theme = HorillaColorTheme.objects.filter(name=name).first()

            # Migrate the old coral default onto the new DSG default name once.
            if theme is None and name == "DSG Indigo Theme (Default)":
                for legacy in _LEGACY_DEFAULT_NAMES:
                    legacy_theme = HorillaColorTheme.objects.filter(name=legacy).first()
                    if legacy_theme:
                        theme = legacy_theme
                        theme.name = name
                        break

            if theme is None:
                theme = HorillaColorTheme.objects.create(name=name, **fields)
                created_count += 1
                self.stdout.write(self.style.SUCCESS(f"Created theme: {theme.name}"))
                continue

            changed = False
            for key, value in fields.items():
                if getattr(theme, key) != value:
                    setattr(theme, key, value)
                    changed = True
            if theme.name != name:
                theme.name = name
                changed = True
            if changed:
                theme.save()
                updated_count += 1
                self.stdout.write(self.style.SUCCESS(f"Updated theme: {theme.name}"))
            else:
                self.stdout.write(f"Unchanged: {theme.name}")

        # Ensure the DSG default is the only is_default theme when syncing.
        dsg_default = HorillaColorTheme.objects.filter(
            name="DSG Indigo Theme (Default)"
        ).first()
        if dsg_default and not dsg_default.is_default:
            dsg_default.is_default = True
            dsg_default.save()
            updated_count += 1
            self.stdout.write(
                self.style.SUCCESS("Set DSG Indigo Theme as the login default")
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"Done. created={created_count} updated={updated_count}"
            )
        )
