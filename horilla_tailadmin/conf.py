"""Mount MIT TailAdmin HTML template static assets when present locally."""

from __future__ import annotations

import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

APP_ROOT = Path(__file__).resolve().parent
VENDOR_ROOT = APP_ROOT / "vendor"
REPO_URL = "https://github.com/TailAdmin/tailadmin-free-tailwind-dashboard-template"
_HTML_MARKERS = ("package.json",)


def _env_path(name: str) -> Path | None:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return None
    path = Path(raw).expanduser().resolve()
    return path if path.is_dir() else None


def vendor_search_roots() -> list[Path]:
    roots: list[Path] = []
    custom = _env_path("TAILADMIN_VENDOR_ROOT")
    if custom:
        roots.append(custom)
    if VENDOR_ROOT.is_dir():
        roots.append(VENDOR_ROOT)
        for child in sorted(VENDOR_ROOT.iterdir()):
            if child.is_dir():
                roots.append(child)
    return roots


def find_html_root() -> Path | None:
    for root in vendor_search_roots():
        if (root / "package.json").is_file():
            return root
        for child in root.iterdir() if root.is_dir() else []:
            if child.is_dir() and (child / "package.json").is_file():
                return child
    return None


def find_assets_dir(html_root: Path | None) -> Path | None:
    if not html_root:
        return None
    for name in ("src", "build", "assets", "public"):
        candidate = html_root / name
        if candidate.is_dir():
            if name == "src" and (candidate / "images").is_dir():
                return candidate
            if name in ("build", "assets", "public"):
                return candidate
    return None


def tailadmin_staticfile_dirs() -> list[tuple[str, str]]:
    entries: list[tuple[str, str]] = []
    html_root = find_html_root()
    assets = find_assets_dir(html_root)
    if assets:
        entries.append((str(assets), "tailadmin"))
    return entries


def vendor_installed() -> bool:
    return find_html_root() is not None


def vendor_status() -> dict:
    html_root = find_html_root()
    assets = find_assets_dir(html_root)
    return {
        "installed": vendor_installed(),
        "vendor_root": str(VENDOR_ROOT),
        "env_override": os.environ.get("TAILADMIN_VENDOR_ROOT", ""),
        "html_root": str(html_root) if html_root else None,
        "assets_dir": str(assets) if assets else None,
        "static_dirs": tailadmin_staticfile_dirs(),
        "official_repo": REPO_URL,
        "license": "MIT",
    }


def log_vendor_status() -> None:
    if vendor_installed():
        status = vendor_status()
        logger.info("TailAdmin vendor detected at %s", status["html_root"])
    else:
        logger.debug(
            "TailAdmin vendor not installed; using horilla_theme tailadmin-*.css. "
            "Clone %s into horilla_tailadmin/vendor/",
            REPO_URL,
        )


def extend_staticfiles_dirs(existing: list) -> list:
    out = list(existing)
    seen = {str(p[0]) if isinstance(p, (list, tuple)) else str(p) for p in out}
    for filesystem_path, prefix in tailadmin_staticfile_dirs():
        if filesystem_path not in seen:
            out.append((filesystem_path, prefix))
            seen.add(filesystem_path)
    return out


def extend_template_loaders(loaders: list, base_dir: Path) -> list:
    return loaders
