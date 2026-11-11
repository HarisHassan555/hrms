import os
import shlex
import sys

import paramiko

HOST = os.environ.get("QARSHI_SSH_HOST", "192.168.168.31")
USER = os.environ.get("QARSHI_SSH_USER", "administrator")
PASSWORD = os.environ.get("QARSHI_SSH_PASSWORD", "")
LOCAL_CMD = os.path.join(
    os.path.dirname(__file__), "..", "base", "management", "commands", "populate_workforce_demo.py"
)
REMOTE_CMD = "/opt/apps/HRMS/base/management/commands/populate_workforce_demo.py"


def main() -> int:
    if not PASSWORD:
        print("Set QARSHI_SSH_PASSWORD", file=sys.stderr)
        return 2

    local_path = os.path.normpath(LOCAL_CMD)
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    print(f"Connecting to {USER}@{HOST}…")
    client.connect(HOST, username=USER, password=PASSWORD, timeout=30)

    sftp = client.open_sftp()
    print(f"Uploading {local_path} → {REMOTE_CMD}")
    sftp.put(local_path, REMOTE_CMD)
    sftp.close()

    inner = (
        f"echo {shlex.quote(PASSWORD)} | sudo -S "
        "docker exec -w /app hrms-web-1 "
        "python manage.py populate_workforce_demo "
        "--employee-email fariarehman41@gmail.com "
        "--employee-password faria1122"
    )
    print("Running populate_workforce_demo (may take several minutes)…")
    _stdin, stdout, stderr = client.exec_command(inner, timeout=7200)
    out = stdout.read().decode("utf-8", errors="replace")
    err = stderr.read().decode("utf-8", errors="replace")
    code = stdout.channel.recv_exit_status()
    if out:
        print(out[-20000:] if len(out) > 20000 else out)
    if err.strip():
        print(err[-6000:], file=sys.stderr)
    client.close()
    print("exit:", code)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
