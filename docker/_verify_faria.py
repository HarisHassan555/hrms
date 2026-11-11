import os
import shlex
import paramiko

PASSWORD = os.environ["QARSHI_SSH_PASSWORD"]
client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect("192.168.168.31", username="administrator", password=PASSWORD, timeout=30)
py = """
from employee.models import Employee
from django.contrib.auth import get_user_model
email='fariarehman41@gmail.com'
u=get_user_model().objects.filter(email__iexact=email).first()
e=Employee.objects.filter(email__iexact=email).first()
print('user', bool(u), 'employee', e.pk if e else None)
if e:
    from attendance.models import Attendance
    print('attendance_rows', Attendance.objects.filter(employee_id=e).count())
    from leave.models import AvailableLeave
    print('leave_balances', AvailableLeave.objects.filter(employee_id=e).count())
"""
cmd = f"echo {shlex.quote(PASSWORD)} | sudo -S docker exec -w /app hrms-web-1 python manage.py shell -c {shlex.quote(py)}"
_i, o, _e = client.exec_command(cmd, timeout=120)
print(o.read().decode())
client.close()
