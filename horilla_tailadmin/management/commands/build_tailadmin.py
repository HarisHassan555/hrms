"""Build TailAdmin vendor assets and copy into horilla_theme static."""

import shutil
import subprocess
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

VENDOR = (
    Path(settings.BASE_DIR)
    / "horilla_tailadmin"
    / "vendor"
    / "tailadmin-free-tailwind-dashboard-template"
)
DEST = (
    Path(settings.BASE_DIR)
    / "horilla_theme"
    / "static"
    / "horilla_theme"
    / "assets"
    / "tailadmin"
    / "build"
)


class Command(BaseCommand):
    help = "Run npm run build in the TailAdmin vendor repo and copy build/ to theme static."

    def handle(self, *args, **options):
        if not (VENDOR / "package.json").is_file():
            raise CommandError(
                f"TailAdmin vendor not found at {VENDOR}. "
                "Clone https://github.com/TailAdmin/tailadmin-free-tailwind-dashboard-template"
            )
        self.stdout.write("Running npm install && npm run build...")
        subprocess.run("npm install", cwd=VENDOR, shell=True, check=True)
        subprocess.run("npm run build", cwd=VENDOR, shell=True, check=True)
        build_dir = VENDOR / "build"
        if not (build_dir / "style.css").is_file():
            raise CommandError("Build did not produce style.css")
        DEST.mkdir(parents=True, exist_ok=True)
        for name in ("style.css", "bundle.js", "favicon.ico"):
            shutil.copy2(build_dir / name, DEST / name)
        src_images = build_dir / "src"
        if src_images.is_dir():
            dest_src = DEST / "src"
            if dest_src.exists():
                shutil.rmtree(dest_src)
            shutil.copytree(src_images, dest_src)
        self.stdout.write(self.style.SUCCESS(f"Copied TailAdmin build to {DEST}"))
