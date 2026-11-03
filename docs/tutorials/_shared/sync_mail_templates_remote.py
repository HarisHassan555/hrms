#!/usr/bin/env python3
"""
Sync local Horilla mail templates onto a remote HRMS via the Settings UI
(Create modal + Summernote body).

  python docs/tutorials/_shared/sync_mail_templates_remote.py
"""

from __future__ import annotations

import json
import os
import re
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

HERE = Path(__file__).resolve().parent
EXPORT = HERE / "mail_templates_export.json"

BASE = os.environ.get("REMOTE_BASE_URL", "http://192.168.168.31:8000").rstrip("/")
USER = os.environ.get("REMOTE_USERNAME", "haris")
PASSWORD = os.environ.get("REMOTE_PASSWORD", "1212")
LIST_URL = f"{BASE}/settings/mail-templates-view/"


def load_templates() -> list[dict]:
    return json.loads(EXPORT.read_text(encoding="utf-8"))


def dismiss(page) -> None:
    try:
        page.evaluate(
            """() => {
              try { if (window.driverObj && window.driverObj.destroy) window.driverObj.destroy(); } catch (e) {}
              document.querySelectorAll('.driver-popover,.driver-overlay').forEach(e => e.remove());
              if (document.body) document.body.classList.remove('driver-active','driver-fade');
            }"""
        )
        page.keyboard.press("Escape")
        page.wait_for_timeout(200)
    except Exception:
        pass


def login(page) -> None:
    page.goto(f"{BASE}/login/", wait_until="domcontentloaded", timeout=60000)
    page.fill('input[name="username"], input#id_username, input[placeholder*="username" i]', USER)
    page.fill('input[name="password"], input#id_password, input[type="password"]', PASSWORD)
    page.click('button[type="submit"], .login-submit, button:has-text("Login")')
    page.wait_for_url(lambda u: "/login" not in u, timeout=45000)
    page.wait_for_timeout(1200)
    dismiss(page)


def open_list(page) -> None:
    page.goto(LIST_URL, wait_until="domcontentloaded", timeout=60000)
    page.wait_for_timeout(2000)
    dismiss(page)


def existing_titles(page) -> set[str]:
    open_list(page)
    titles = set()
    for el in page.locator("h3").all():
        try:
            t = (el.inner_text() or "").strip()
            if t:
                titles.add(t)
        except Exception:
            pass
    # Also card headings / stronger matches from body text lines that look like titles
    body = page.inner_text("body")
    for t in load_templates():
        if t["title"] in body:
            titles.add(t["title"])
    return titles


def sanitize_body_for_form(html: str) -> str:
    """
    Form clean_body() bleach-allows only a limited tag set (no div).
    Convert common wrapper divs to p so content survives saving.
    """
    html = re.sub(r"</?div\b[^>]*>", lambda m: "</p>" if m.group(0).startswith("</") else "<p>", html, flags=re.I)
    # Collapse empty consecutive p
    html = re.sub(r"(<p>\s*</p>\s*)+", "<p><br></p>", html)
    return html


def set_body(page, html: str) -> None:
    html = sanitize_body_for_form(html)
    result = page.evaluate(
        """(html) => {
          const $ = window.jQuery || window.$;
          const ta = document.querySelector('#id_body, textarea[name="body"]');
          if ($ && ta && $(ta).data('summernote')) {
            $(ta).summernote('code', html);
            $(ta).val(html);
            return 'summernote-ready';
          }
          if ($ && ta) {
            try {
              // init if needed then set
              if (!$(ta).next('.note-editor').length) {
                $(ta).summernote({height: 300, dialogsInBody: true});
              }
              $(ta).summernote('code', html);
              $(ta).val(html);
              return 'summernote-init';
            } catch (e) { /* fall through */ }
          }
          if (ta) {
            ta.style.display = 'block';
            ta.value = html;
            ta.dispatchEvent(new Event('input', {bubbles:true}));
            ta.dispatchEvent(new Event('change', {bubbles:true}));
            return 'textarea';
          }
          const editable = document.querySelector('.note-editable');
          if (editable) {
            editable.innerHTML = html;
            if (ta) ta.value = html;
            return 'note-editable';
          }
          return null;
        }""",
        html,
    )
    if not result:
        raise RuntimeError("body editor not found")
    page.wait_for_timeout(500)


def _csrf_token(page) -> str:
    cookies = page.context.cookies()
    for c in cookies:
        if c.get("name") == "csrftoken":
            return c.get("value") or ""
    # Fallback from DOM
    try:
        return page.evaluate(
            """() => {
              const m = document.querySelector('input[name=csrfmiddlewaretoken]');
              if (m) return m.value;
              const meta = document.querySelector('meta[name=csrf-token]');
              return meta ? meta.content : '';
            }"""
        ) or ""
    except Exception:
        return ""


def create_template(page, title: str, body: str) -> str:
    """
    Prefer authenticated POST to /create-mail-template/ (same form the UI uses).
    Falls back to the Create modal if POST fails.
    """
    open_list(page)
    csrf = _csrf_token(page)
    if not csrf:
        raise RuntimeError("No CSRF token — are we logged in?")

    clean_body = sanitize_body_for_form(body or "<p></p>")
    resp = page.request.post(
        f"{BASE}/create-mail-template/",
        form={
            "csrfmiddlewaretoken": csrf,
            "title": title[:100],
            "body": clean_body,
            "is_active": "unknown",  # HiddenInput often posts this
        },
        headers={
            "Referer": LIST_URL,
            "X-CSRFToken": csrf,
        },
    )
    status = resp.status
    text = ""
    try:
        text = resp.text()
    except Exception:
        pass

    # 200/302 typically success; form errors return 200 with HTML errors
    if status in (200, 302, 303) and "errorlist" not in text and "This field is required" not in text:
        # Confirm on list
        open_list(page)
        if title in page.inner_text("body"):
            return f"created(post:{status})"
        # Unique constraint / already exists
        if "already" in text.lower() or "unique" in text.lower():
            return "exists"
        return f"submitted(post:{status})"

    # Modal fallback
    page.evaluate(
        """() => {
          const btn = document.querySelector('[hx-get*="mail-template-create-form"]');
          if (btn) { btn.click(); return 'btn'; }
          if (window.htmx) {
            htmx.ajax('GET', '/mail-template-create-form/', {
              target: '#objectCreateModalTarget',
              swap: 'innerHTML'
            });
            const modal = document.querySelector('#objectCreateModal');
            if (modal) {
              modal.classList.add('oh-modal--show');
              modal.style.display = 'block';
            }
            return 'htmx';
          }
          return null;
        }"""
    )
    title_input = page.locator('#id_title, input[name="title"]').first
    title_input.wait_for(state="visible", timeout=20000)
    page.wait_for_timeout(800)
    title_input.fill(title[:100])
    set_body(page, body)
    page.locator(
        '#objectCreateModal button[type="submit"], #genericModal button[type="submit"], '
        'form button[type="submit"]'
    ).first.click(force=True)
    page.wait_for_timeout(2500)
    open_list(page)
    if title in page.inner_text("body"):
        return "created(modal)"
    return f"failed(post:{status})"


def main() -> None:
    templates = load_templates()
    print(f"Remote {BASE} as {USER} — {len(templates)} local templates")

    created = skipped = failed = 0
    results = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        page = context.new_page()
        page.set_default_timeout(30000)

        login(page)
        have = existing_titles(page)
        print(f"Already on remote: {sorted(have)}")

        for i, t in enumerate(templates, 1):
            title = t["title"]
            print(f"\n[{i}/{len(templates)}] {title}")
            if title in have:
                print("  skip (exists)")
                skipped += 1
                results.append((title, "skipped"))
                continue
            try:
                status = create_template(page, title, t.get("body") or "")
                print(f"  -> {status}")
                if status in ("created", "submitted"):
                    created += 1
                    have.add(title)
                else:
                    failed += 1
                results.append((title, status))
            except Exception as exc:
                print(f"  FAILED: {exc}")
                failed += 1
                results.append((title, f"FAILED: {exc}"))
                dismiss(page)
            time.sleep(0.3)

        # Final inventory
        final = existing_titles(page)
        print("\n=== FINAL REMOTE TITLES ===")
        for t in sorted(final):
            if any(t == x["title"] for x in templates) or t.startswith("["):
                print(" *", t)

        context.close()
        browser.close()

    print("\n=== SUMMARY ===")
    print(f"created={created} skipped={skipped} failed={failed}")
    for title, status in results:
        print(f" {status}: {title}")


if __name__ == "__main__":
    main()
