"""Report whether licensed Vristo vendor files are mounted."""

from django.core.management.base import BaseCommand

from horilla_vristo.conf import vendor_status


class Command(BaseCommand):
    help = (
        "Show Vristo vendor integration status. Vristo is a commercial "
        "ThemeForest template; there is no pip package."
    )

    def handle(self, *args, **options):
        status = vendor_status()
        self.stdout.write("Vristo integration (horilla_vristo)")
        self.stdout.write("-" * 40)
        self.stdout.write(status["official_note"])
        self.stdout.write(f"Purchase: {status['purchase_url']}")
        self.stdout.write(f"Docs:     {status['docs_url']}")
        self.stdout.write("")
        self.stdout.write(f"Vendor directory: {status['vendor_root']}")
        if status["env_override"]:
            self.stdout.write(f"VRISTO_VENDOR_ROOT: {status['env_override']}")
        self.stdout.write(f"Installed: {status['installed']}")
        self.stdout.write(f"HTML root: {status['html_root'] or '(not found)'}")
        self.stdout.write(f"Django root: {status['django_root'] or '(not found)'}")
        self.stdout.write(f"Assets: {status['assets_dir'] or '(not found)'}")
        if status["template_dirs"]:
            self.stdout.write("Template dirs:")
            for path in status["template_dirs"]:
                self.stdout.write(f"  - {path}")
        if status["static_dirs"]:
            self.stdout.write("Static mounts:")
            for filesystem_path, prefix in status["static_dirs"]:
                self.stdout.write(f"  - {filesystem_path} -> static/{prefix}/")
        if not status["installed"]:
            self.stdout.write("")
            self.stdout.write(
                self.style.WARNING(
                    "No vendor tree detected. See horilla_vristo/vendor/README.txt"
                )
            )
