import os
import shlex
import paramiko

password = os.environ["QARSHI_SSH_PASSWORD"]
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("192.168.168.31", username="administrator", password=password, timeout=30)
# Use dev compose (inline env); prod compose needs missing .env
cmd = (
    f"echo {shlex.quote(password)} | sudo -S bash -lc "
    f"'cd /opt/apps/HRMS && docker compose up --build -d && docker compose ps'"
)
print("Running rebuild (may take several minutes)...")
_i, o, e = c.exec_command(cmd, get_pty=True, timeout=3600)
out = o.read().decode("utf-8", errors="replace")
print(out[-8000:] if len(out) > 8000 else out)
code = o.channel.recv_exit_status()
print("exit:", code)
c.close()
raise SystemExit(code)
