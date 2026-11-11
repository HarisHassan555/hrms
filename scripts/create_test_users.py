"""One-off helper: create testemployee / testmanager login accounts.

Run inside the app container:
  python manage.py shell -c "import importlib.util; s=importlib.util.spec_from_file_location('ctu','scripts/create_test_users.py'); m=importlib.util.module_from_spec(s); s.loader.exec_module(m); m.run()"
"""
from django.contrib.auth.models import Group

from base.models import Company, CompanyGroupAssignment, Department, EmployeeShift, WorkType
from base.role_defaults import assign_default_employee_role
from employee.models import Employee, EmployeeWorkInformation
from horilla_auth.models import HorillaUser

PASSWORD = "1212"


def run():
    company = Company.objects.filter(hq=True).first() or Company.objects.order_by("pk").first()
    if not company:
        raise SystemExit("No company found; initialize the database first.")

    dept = Department.objects.filter(company_id=company).first() or Department.objects.first()
    work_type = WorkType.objects.filter(company_id=company).first() or WorkType.objects.first()
    shift = EmployeeShift.objects.filter(company_id=company).first() or EmployeeShift.objects.first()

    employee_group = Group.objects.filter(name="Employee").first()
    manager_group = Group.objects.filter(name="Manager").first()
    if not employee_group or not manager_group:
        raise SystemExit("Default HRMS groups missing; run migrations/post_migrate sync.")

    def upsert_account(username, email, first_name, last_name):
        user = HorillaUser.objects.filter(username=username).first()
        if user is None:
            user = HorillaUser.objects.filter(email=email).first()
        if user is None:
            user = HorillaUser(username=username, email=email)
        user.username = username
        user.email = email
        user.first_name = first_name
        user.last_name = last_name
        user.is_active = True
        user.is_staff = False
        user.is_superuser = False
        user.set_password(PASSWORD)
        user.save()
        return user

    def upsert_employee(user, email, first_name, last_name):
        employee = Employee.objects.filter(employee_user_id=user).first()
        if employee is None:
            employee = Employee.objects.filter(email=email).first()
        if employee is None:
            employee = Employee(email=email)
        employee.employee_user_id = user
        employee.employee_first_name = first_name
        employee.employee_last_name = last_name
        employee.is_active = True
        employee.save()
        return employee

    def ensure_work_info(employee, reporting_manager=None):
        info, _ = EmployeeWorkInformation.objects.get_or_create(employee_id=employee)
        info.company_id = company
        if dept:
            info.department_id = dept
        if work_type:
            info.work_type_id = work_type
        if shift:
            info.shift_id = shift
        info.reporting_manager_id = reporting_manager
        info.email = employee.email
        info.save()
        return info

    mgr_user = upsert_account("testmanager", "testmanager@test.local", "Test", "Manager")
    mgr_emp = upsert_employee(mgr_user, "testmanager@test.local", "Test", "Manager")
    ensure_work_info(mgr_emp, reporting_manager=None)

    CompanyGroupAssignment.objects.filter(user=mgr_user).delete()
    mgr_user.groups.clear()
    CompanyGroupAssignment.objects.get_or_create(
        user=mgr_user, company=company, group=manager_group
    )
    CompanyGroupAssignment.sync_user_group_membership(mgr_user, manager_group)

    emp_user = upsert_account("testemployee", "testemployee@test.local", "Test", "Employee")
    emp = upsert_employee(emp_user, "testemployee@test.local", "Test", "Employee")
    ensure_work_info(emp, reporting_manager=mgr_emp)
    assign_default_employee_role(emp_user, company=company, replace=True)

    print("Created/updated test accounts (password: 1212)")
    print(f"  testmanager -> groups: {list(mgr_user.groups.values_list('name', flat=True))}")
    print(f"  testemployee -> groups: {list(emp_user.groups.values_list('name', flat=True))}")
    print(f"  testemployee reports to: {emp.employee_work_info.reporting_manager_id}")


if __name__ == "__main__":
    run()
