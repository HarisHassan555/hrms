import os
import paramiko

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(
    "192.168.168.31",
    username="administrator",
    password=os.environ["QARSHI_SSH_PASSWORD"],
    timeout=30,
)
for cmd in [
    "sudo -n docker ps --format 'table {{.Names}}\t{{.Status}}' 2>&1 | head -15",
    "sudo -n bash -lc 'cd /opt/apps/HRMS && docker compose ps' 2>&1",
]:
    print("===", cmd)
    _i, o, _e = c.exec_command(cmd, get_pty=True, timeout=60)
    print(o.read().decode("utf-8", errors="replace"))
c.close()
