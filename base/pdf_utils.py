"""
Shared pdfkit / wkhtmltopdf helpers.

Payslips, mail PDF attachments, and API PDF endpoints all go through
wkhtmltopdf. Resolve the binary once and render HTML to PDF in one place
so Docker, local, and CI installs do not each invent their own lookup.

wkhtmltopdf often exits with code 1 when a template references unreachable
absolute URLs (company logos on localhost, CDNs blocked, etc.) even when
``--load-error-handling ignore`` is set — yet it still writes a valid PDF.
We accept that PDF rather than surfacing a hard failure to the user.
"""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
import tempfile
from functools import lru_cache

import pdfkit

logger = logging.getLogger(__name__)

_CANDIDATE_PATHS = (
    "/usr/local/bin/wkhtmltopdf",
    "/usr/bin/wkhtmltopdf",
    "/bin/wkhtmltopdf",
)


@lru_cache(maxsize=1)
def get_wkhtmltopdf_path() -> str:
    """
    Return the absolute path to wkhtmltopdf.

    Order: ``WKHTMLTOPDF_PATH`` / ``WKHTMLTOPDF_CMD`` env, then common
    install locations, then ``PATH``.
    """
    for env_name in ("WKHTMLTOPDF_PATH", "WKHTMLTOPDF_CMD"):
        env_path = (os.environ.get(env_name) or "").strip().strip('"')
        if env_path and os.path.isfile(env_path) and os.access(env_path, os.X_OK):
            return env_path

    for candidate in _CANDIDATE_PATHS:
        if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
            return candidate

    which = shutil.which("wkhtmltopdf")
    if which and os.path.isfile(which):
        return which

    raise FileNotFoundError(
        "wkhtmltopdf executable not found. Install wkhtmltopdf "
        "(https://github.com/JazzCore/python-pdfkit/wiki/Installing-wkhtmltopdf) "
        "or set WKHTMLTOPDF_PATH to the binary."
    )


@lru_cache(maxsize=1)
def get_pdfkit_config():
    """pdfkit.configuration bound to the resolved wkhtmltopdf binary."""
    path = get_wkhtmltopdf_path()
    logger.debug("Using wkhtmltopdf at %s", path)
    return pdfkit.configuration(wkhtmltopdf=path)


DEFAULT_PDF_OPTIONS = {
    "page-size": "A4",
    "margin-top": "10mm",
    "margin-bottom": "10mm",
    "margin-left": "10mm",
    "margin-right": "10mm",
    "encoding": "UTF-8",
    "enable-local-file-access": None,
    "dpi": "300",
    "zoom": "1.3",
    "footer-center": "[page]/[topage]",
    # Payslip HTML references host logos / CDNs; inside Docker those
    # absolute URLs often fail. Ignore so the PDF still generates.
    "load-error-handling": "ignore",
    "load-media-error-handling": "ignore",
}


def _options_to_args(options: dict) -> list[str]:
    """Convert pdfkit-style options to wkhtmltopdf CLI args."""
    args: list[str] = []
    for key, value in options.items():
        flag = f"--{key}"
        if value is None or value is True:
            args.append(flag)
        elif value is False:
            continue
        elif isinstance(value, (list, tuple)):
            # e.g. custom-header: [("Cookie", "...")] ->
            # --custom-header Cookie <value>
            for item in value:
                args.append(flag)
                if isinstance(item, (list, tuple)):
                    args.extend(str(part) for part in item)
                else:
                    args.append(str(item))
        else:
            args.extend([flag, str(value)])
    return args


def html_to_pdf(html_content: str, options: dict | None = None) -> bytes:
    """Render HTML to PDF bytes using the shared wkhtmltopdf binary."""
    pdf_options = dict(DEFAULT_PDF_OPTIONS)
    if options:
        pdf_options.update(options)

    wkhtml = get_wkhtmltopdf_path()
    html_path = None
    pdf_path = None
    try:
        with tempfile.NamedTemporaryFile(
            suffix=".html", delete=False, mode="w", encoding="utf-8"
        ) as html_file:
            html_file.write(html_content)
            html_path = html_file.name
        pdf_path = f"{html_path}.pdf"

        cmd = [wkhtml, *_options_to_args(pdf_options), html_path, pdf_path]
        proc = subprocess.run(cmd, capture_output=True, text=True)

        if os.path.isfile(pdf_path) and os.path.getsize(pdf_path) > 0:
            with open(pdf_path, "rb") as pdf_file:
                data = pdf_file.read()
            if data.startswith(b"%PDF"):
                if proc.returncode != 0:
                    logger.warning(
                        "wkhtmltopdf exited %s but produced a PDF (%s bytes): %s",
                        proc.returncode,
                        len(data),
                        (proc.stderr or proc.stdout or "").strip()[-500:],
                    )
                return data

        stderr = (proc.stderr or proc.stdout or "").strip()
        raise OSError(
            "wkhtmltopdf reported an error:\n"
            + (stderr or f"exit code {proc.returncode}")
        )
    finally:
        for path in (html_path, pdf_path):
            if path and os.path.exists(path):
                try:
                    os.unlink(path)
                except OSError:
                    pass
