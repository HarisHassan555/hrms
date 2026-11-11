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
cmds = [
    "cd /opt/apps/HRMS && git rev-parse --short HEAD",
    "cd /opt/apps/HRMS && ls -la .env docker-compose*.yml 2>&1",
    'docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Image}}"',
    "cd /opt/apps/HRMS && docker compose ps 2>&1 | head -25",
]
for cmd in cmds:
    print("===", cmd)
    _i, o, _e = c.exec_command(cmd, get_pty=True, timeout=120)
    print(o.read().decode("utf-8", errors="replace"))
c.close()
