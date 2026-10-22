from django.core.management.base import BaseCommand

from horilla_tailadmin.conf import vendor_status


class Command(BaseCommand):
    help = "Show TailAdmin MIT vendor integration status."

    def handle(self, *args, **options):
        status = vendor_status()
        self.stdout.write("TailAdmin integration (horilla_tailadmin)")
        self.stdout.write("-" * 40)
        self.stdout.write(f"Official repo (MIT): {status['official_repo']}")
        self.stdout.write(f"Vendor directory: {status['vendor_root']}")
        if status["env_override"]:
            self.stdout.write(f"TAILADMIN_VENDOR_ROOT: {status['env_override']}")
        self.stdout.write(f"Installed: {status['installed']}")
        self.stdout.write(f"HTML root: {status['html_root'] or '(not found)'}")
        self.stdout.write(f"Assets: {status['assets_dir'] or '(not found)'}")
        if status["static_dirs"]:
            for path, prefix in status["static_dirs"]:
                self.stdout.write(f"Static: {path} -> /static/{prefix}/")
        if not status["installed"]:
            self.stdout.write("")
            self.stdout.write(
                self.style.WARNING(
                    "Clone the MIT repo into horilla_tailadmin/vendor/ — see vendor/README.txt"
                )
            )
