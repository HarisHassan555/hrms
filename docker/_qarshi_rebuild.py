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
    "sudo docker ps --format 'table {{.Names}}\t{{.Status}}' 2>&1",
    "groups administrator 2>&1",
    "ls -la /opt/apps/HRMS/.env* 2>&1",
    "sudo bash -lc 'cd /opt/apps/HRMS && docker compose up --build -d' 2>&1",
    "sudo bash -lc 'cd /opt/apps/HRMS && docker compose ps' 2>&1",
]
for cmd in cmds:
    print("===", cmd[:120])
    _i, o, e = c.exec_command(cmd, get_pty=True, timeout=3600)
    out = o.read().decode("utf-8", errors="replace")
    err = e.read().decode("utf-8", errors="replace")
    print(out)
    if err.strip():
        print("STDERR:", err)
c.close()
