"""
Resolve licensed Vristo (SB Themes) files under horilla_vristo/vendor/.

Official product: https://themeforest.net/item/vristo-multipurpose-tailwind-css-admin-template/44221232
Docs / demo: https://vristo.sbthemes.com/ , https://html.vristo.sbthemes.com/

There is no official PyPI or public GitHub package for Vristo; purchase includes
HTML, and often separate stacks (React, Laravel, Django starter folders).
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Iterable

logger = logging.getLogger(__name__)

APP_ROOT = Path(__file__).resolve().parent
VENDOR_ROOT = APP_ROOT / "vendor"

# Subfolders users typically extract from the ThemeForest zip (any match is used).
_HTML_MARKERS = ("package.json", "tailwind.config.js", "index.html")
_DJANGO_MARKERS = ("manage.py",)
_ASSETS_DIR_NAMES = ("assets", "static")


def _env_path(name: str) -> Path | None:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return None
    path = Path(raw).expanduser().resolve()
    return path if path.is_dir() else None


def vendor_search_roots() -> list[Path]:
    """Directories to scan for a Vristo HTML or Django tree."""
    roots: list[Path] = []
    custom = _env_path("VRISTO_VENDOR_ROOT")
    if custom:
        roots.append(custom)
    if VENDOR_ROOT.is_dir():
        roots.append(VENDOR_ROOT)
        for child in sorted(VENDOR_ROOT.iterdir()):
            if child.is_dir():
                roots.append(child)
    return roots


def _has_markers(directory: Path, markers: Iterable[str]) -> bool:
    return all((directory / name).is_file() for name in markers)


def find_html_root() -> Path | None:
    """Root of the Vristo HTML / Tailwind package (contains package.json + index.html)."""
    for root in vendor_search_roots():
        if _has_markers(root, _HTML_MARKERS):
            return root
        for child in root.iterdir() if root.is_dir() else []:
            if child.is_dir() and _has_markers(child, _HTML_MARKERS):
                return child
    return None


def find_django_root() -> Path | None:
    """Root of an optional Vristo Django starter from the license bundle."""
    for root in vendor_search_roots():
        if _has_markers(root, _DJANGO_MARKERS):
            return root
        django_sub = root / "django"
        if django_sub.is_dir() and _has_markers(django_sub, _DJANGO_MARKERS):
            return django_sub
        for child in root.iterdir() if root.is_dir() else []:
            if child.is_dir() and _has_markers(child, _DJANGO_MARKERS):
                return child
    return None


def find_assets_dir(html_root: Path | None) -> Path | None:
    if not html_root:
        return None
    for name in _ASSETS_DIR_NAMES:
        candidate = html_root / name
        if candidate.is_dir():
            return candidate
    return None


def vristo_template_dirs() -> list[Path]:
    """Extra template dirs from vendor Django starter, if installed."""
    dirs: list[Path] = []
    django_root = find_django_root()
    if not django_root:
        return dirs
    for relative in ("templates", "theme/templates"):
        path = django_root / relative
        if path.is_dir():
            dirs.append(path)
    return dirs


def vristo_staticfile_dirs() -> list[tuple[str, str]]:
    """
    Static file dirs for django.contrib.staticfiles.

    Returns list of (filesystem_path, url_prefix) tuples.
    """
    entries: list[tuple[str, str]] = []
    html_root = find_html_root()
    assets = find_assets_dir(html_root)
    if assets:
        entries.append((str(assets), "vristo"))
    django_root = find_django_root()
    if django_root:
        for relative in ("static", "assets"):
            path = django_root / relative
            if path.is_dir():
                entries.append((str(path), "vristo-django"))
    return entries


def vendor_installed() -> bool:
    return bool(find_html_root() or find_django_root())


def vendor_status() -> dict:
    html_root = find_html_root()
    django_root = find_django_root()
    assets = find_assets_dir(html_root)
    return {
        "installed": vendor_installed(),
        "vendor_root": str(VENDOR_ROOT),
        "env_override": os.environ.get("VRISTO_VENDOR_ROOT", ""),
        "html_root": str(html_root) if html_root else None,
        "django_root": str(django_root) if django_root else None,
        "assets_dir": str(assets) if assets else None,
        "template_dirs": [str(p) for p in vristo_template_dirs()],
        "static_dirs": vristo_staticfile_dirs(),
        "official_package": None,
        "official_note": (
            "Vristo is sold by sbthemes on ThemeForest; it is not published "
            "on PyPI or npm as an installable library."
        ),
        "purchase_url": (
            "https://themeforest.net/item/vristo-multipurpose-tailwind-css-admin-template/44221232"
        ),
        "docs_url": "https://vristo.sbthemes.com/documentation/installation",
    }


def log_vendor_status() -> None:
    if vendor_installed():
        status = vendor_status()
        logger.info(
            "Vristo vendor assets detected (html=%s, django=%s)",
            status["html_root"],
            status["django_root"],
        )
    else:
        logger.debug(
            "Vristo vendor not installed; using horilla_theme Vristo-inspired CSS. "
            "See horilla_vristo/vendor/README.txt"
        )


def extend_template_loaders(loaders: list, base_dir: Path) -> list:
    """Prepend vendor template loader entries after horilla_dbtemplate."""
    dirs = vristo_template_dirs()
    if not dirs:
        return loaders
    new_loaders = list(loaders)
    insert_at = 1
    for path in dirs:
        entry = ("django.template.loaders.filesystem.Loader", [path])
        new_loaders.insert(insert_at, entry)
        insert_at += 1
    return new_loaders


def extend_staticfiles_dirs(existing: list) -> list:
    """Append vendor static dirs without duplicating paths."""
    out = list(existing)
    seen = {str(p[0]) if isinstance(p, (list, tuple)) else str(p) for p in out}
    for filesystem_path, prefix in vristo_staticfile_dirs():
        if filesystem_path not in seen:
            out.append((filesystem_path, prefix))
            seen.add(filesystem_path)
    return out
