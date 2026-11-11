#!/usr/bin/env python3
"""
Pull latest HRMS on the Qarshi server and rebuild Docker.

Credentials via environment (never commit passwords):
  QARSHI_SSH_HOST      default 192.168.168.31
  QARSHI_SSH_PORT      default 22
  QARSHI_SSH_USER      default administrator
  QARSHI_SSH_PASSWORD  required
  QARSHI_REPO_DIR      optional; auto-detect if unset
  QARSHI_GIT_BRANCH    default new_ui
"""

from __future__ import annotations

import os
import sys

try:
    import paramiko
except ImportError:
    print("Install paramiko: pip install paramiko", file=sys.stderr)
    sys.exit(1)

HOST = os.environ.get("QARSHI_SSH_HOST", "192.168.168.31")
PORT = int(os.environ.get("QARSHI_SSH_PORT", "22"))
USER = os.environ.get("QARSHI_SSH_USER", "administrator")
PASSWORD = os.environ.get("QARSHI_SSH_PASSWORD", "")
REPO_DIR = os.environ.get("QARSHI_REPO_DIR", "").strip()
BRANCH = os.environ.get("QARSHI_GIT_BRANCH", "new_ui")


def run(client: paramiko.SSHClient, cmd: str, timeout: int = 600) -> tuple[int, str, str]:
    print(f"\n>>> {cmd[:200]}{'…' if len(cmd) > 200 else ''}\n")
    _stdin, stdout, stderr = client.exec_command(cmd, timeout=timeout, get_pty=True)
    out = stdout.read().decode("utf-8", errors="replace")
    err = stderr.read().decode("utf-8", errors="replace")
    code = stdout.channel.recv_exit_status()
    if out:
        print(out.rstrip())
    if err:
        print(err.rstrip(), file=sys.stderr)
    return code, out, err


def main() -> int:
    if not PASSWORD:
        print("Set QARSHI_SSH_PASSWORD in the environment.", file=sys.stderr)
        return 2

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    print(f"Connecting to {USER}@{HOST}:{PORT} …")
    try:
        client.connect(
            HOST,
            port=PORT,
            username=USER,
            password=PASSWORD,
            timeout=30,
            banner_timeout=30,
            auth_timeout=30,
        )
    except Exception as exc:
        print(f"SSH failed: {exc}", file=sys.stderr)
        print(
            "If the host timed out, connect this PC to the office LAN or VPN, then retry.",
            file=sys.stderr,
        )
        return 1

    _, uname_out, _ = run(client, "uname -s 2>/dev/null || echo Windows", timeout=60)
    is_windows = "Windows" in uname_out or "NT" in uname_out

    if is_windows:
        repo_ps = REPO_DIR or ""
        detect_ps = (
            f"$r = '{repo_ps}'; "
            "if ($r -and (Test-Path (Join-Path $r '.git'))) { $r } "
            "else { "
            "$candidates = @('C:\\HRMS','C:\\DSG\\HRMS','D:\\HRMS','C:\\Users\\Administrator\\HRMS'); "
            "foreach ($c in $candidates) { if (Test-Path (Join-Path $c '.git')) { $c; exit 0 } }; "
            "Get-ChildItem -Path C:\\,D:\\ -Filter HRMS -Directory -ErrorAction SilentlyContinue "
            "| Where-Object { Test-Path (Join-Path $_.FullName '.git') } "
            "| Select-Object -ExpandProperty FullName -First 1 "
            "}"
        )
        _, out, _ = run(
            client,
            f'powershell -NoProfile -Command "{detect_ps}"',
            timeout=180,
        )
        repo = out.strip().splitlines()[-1].strip() if out.strip() else ""
        if not repo:
            print("Could not find HRMS git directory. Set QARSHI_REPO_DIR.", file=sys.stderr)
            client.close()
            return 1
        print(f"Using repo: {repo}")
        deploy_ps = (
            f"Set-Location '{repo}'; "
            f"git fetch origin; git checkout {BRANCH}; git pull --ff-only origin {BRANCH}; "
            "if (Test-Path docker-compose.prod.yml) { "
            f"docker compose -f docker-compose.prod.yml down; "
            f"docker compose -f docker-compose.prod.yml up --build -d; "
            f"docker compose -f docker-compose.prod.yml ps "
            "} else { "
            "docker compose down; docker compose up --build -d; docker compose ps "
            "}"
        )
        code, _, _ = run(
            client,
            f'powershell -NoProfile -Command "{deploy_ps}"',
            timeout=3600,
        )
    else:
        repo = REPO_DIR
        detect_sh = (
            f'if [ -n "{repo}" ] && [ -d "{repo}/.git" ]; then echo "{repo}"; else '
            'for d in "$HOME/HRMS" /opt/HRMS /var/www/HRMS; do '
            '[ -d "$d/.git" ] && echo "$d" && exit 0; done; '
            'find "$HOME" /opt /var/www -maxdepth 4 -type d -name HRMS 2>/dev/null | head -1; fi'
        )
        _, out, _ = run(client, f"bash -lc {repr(detect_sh)}", timeout=120)
        repo = (out.strip().splitlines() or [""])[-1].strip()
        if not repo:
            print("Could not find HRMS git directory. Set QARSHI_REPO_DIR.", file=sys.stderr)
            client.close()
            return 1
        print(f"Using repo: {repo}")
        deploy_sh = (
            f"set -e; cd '{repo}'; git fetch origin; git checkout {BRANCH}; "
            f"git pull --ff-only origin {BRANCH}; "
            "if [ -f docker-compose.prod.yml ]; then "
            "docker compose -f docker-compose.prod.yml down && "
            "docker compose -f docker-compose.prod.yml up --build -d && "
            "docker compose -f docker-compose.prod.yml ps; "
            "else docker compose down && docker compose up --build -d && docker compose ps; fi"
        )
        code, _, _ = run(client, f"bash -lc {repr(deploy_sh)}", timeout=3600)

    client.close()
    return code


if __name__ == "__main__":
    raise SystemExit(main())
