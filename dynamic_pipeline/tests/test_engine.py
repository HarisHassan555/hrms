"""Pipeline resolution: AND, OR, roles, and the reporting line."""

from django.contrib.auth.models import Group
from django.test import TestCase

from base.models import CompanyGroupAssignment
from dynamic_pipeline.models import PipelineRun, PipelineStep, StepAssignee
from dynamic_pipeline.seed import seed_processes
from dynamic_pipeline.services import (
    PipelineError,
    decide,
    replace_pipeline,
    start_run_if_configured,
)
from horilla.testkit import make_company, make_employee, make_user


class EngineTests(TestCase):
    def setUp(self):
        seed_processes()
        self.company = make_company("Pipeline Co")
        self.manager_user = make_user("manager")
        self.employee_user = make_user("employee")
        self.hr_user = make_user("hr")
        self.manager = make_employee(
            company=self.company,
            email="manager@pipeline.test",
            first_name="Mina",
            last_name="Manager",
            user=self.manager_user,
        )
        self.employee = make_employee(
            company=self.company,
            email="employee@pipeline.test",
            first_name="Ali",
            last_name="Raza",
            user=self.employee_user,
        )
        self.hr = make_employee(
            company=self.company,
            email="hr@pipeline.test",
            first_name="Hira",
            last_name="Khan",
            user=self.hr_user,
        )
        from employee.models import EmployeeWorkInformation

        EmployeeWorkInformation.objects.filter(employee_id=self.employee).update(
            reporting_manager_id=self.manager
        )
        self.employee = type(self.employee).objects.select_related(
            "employee_work_info"
        ).get(pk=self.employee.pk)
        self.hr_group = Group.objects.create(name="HR")
        CompanyGroupAssignment.objects.create(
            user=self.hr_user, company=self.company, group=self.hr_group
        )
        self.hr_user.groups.add(self.hr_group)

    def _target(self, pk):
        from leave.models import LeaveRequest

        # A real model is required so the content type can be stored.
        # The engine only reads the primary key and the model class.
        return LeaveRequest(pk=pk)

    def test_manager_follows_the_reporting_line(self):
        from dynamic_pipeline.models import Process

        process = Process.objects.get(code="leave_request")
        replace_pipeline(
            self.company,
            process,
            [
                {
                    "name": "Manager",
                    "mode": PipelineStep.OR,
                    "assignees": [{"kind": StepAssignee.REPORTING_MANAGER}],
                }
            ],
        )
        run = start_run_if_configured(
            "leave_request", self._target(11), self.employee
        )
        slot = run.slots.get()
        self.assertEqual(slot.employee_id, self.manager.pk)
        self.assertFalse(_can(run, self.employee_user))
        updated = decide(run, self.manager_user, "approved")
        self.assertEqual(updated.status, PipelineRun.APPROVED)

    def test_and_waits_for_every_slot_and_or_accepts_one(self):
        from dynamic_pipeline.models import Process

        process = Process.objects.get(code="asset_request")
        replace_pipeline(
            self.company,
            process,
            [
                {
                    "name": "Both",
                    "mode": PipelineStep.AND,
                    "assignees": [
                        {
                            "kind": StepAssignee.EMPLOYEE,
                            "employee_id": self.manager.pk,
                        },
                        {"kind": StepAssignee.ROLE, "role_id": self.hr_group.pk},
                    ],
                }
            ],
        )
        run = start_run_if_configured("asset_request", self._target(12), self.employee)
        waiting = decide(run, self.manager_user, "approved")
        self.assertEqual(waiting.status, PipelineRun.PENDING)
        finished = decide(waiting, self.hr_user, "approved")
        self.assertEqual(finished.status, PipelineRun.APPROVED)

        replace_pipeline(
            self.company,
            process,
            [
                {
                    "name": "Either",
                    "mode": PipelineStep.OR,
                    "assignees": [
                        {
                            "kind": StepAssignee.EMPLOYEE,
                            "employee_id": self.manager.pk,
                        },
                        {"kind": StepAssignee.ROLE, "role_id": self.hr_group.pk},
                    ],
                }
            ],
        )
        or_run = start_run_if_configured(
            "asset_request", self._target(13), self.employee
        )
        or_done = decide(or_run, self.hr_user, "approved")
        self.assertEqual(or_done.status, PipelineRun.APPROVED)

    def test_reject_stops_the_run(self):
        from dynamic_pipeline.models import Process

        process = Process.objects.get(code="attendance_request")
        replace_pipeline(
            self.company,
            process,
            [
                {
                    "name": "Manager",
                    "mode": PipelineStep.OR,
                    "assignees": [
                        {
                            "kind": StepAssignee.EMPLOYEE,
                            "employee_id": self.manager.pk,
                        }
                    ],
                }
            ],
        )
        run = start_run_if_configured(
            "attendance_request", self._target(14), self.employee
        )
        rejected = decide(run, self.manager_user, "rejected", "Dates overlap")
        self.assertEqual(rejected.status, PipelineRun.REJECTED)

    def test_more_than_ten_steps_is_rejected(self):
        from dynamic_pipeline.models import Process

        process = Process.objects.get(code="shift_request")
        steps = [
            {
                "name": f"Step {index}",
                "mode": PipelineStep.OR,
                "assignees": [{"kind": StepAssignee.REPORTING_MANAGER}],
            }
            for index in range(1, 12)
        ]
        with self.assertRaises(PipelineError):
            replace_pipeline(self.company, process, steps)

    def test_unconfigured_process_does_not_start_a_run(self):
        run = start_run_if_configured(
            "overtime_request", self._target(15), self.employee
        )
        self.assertIsNone(run)


def _can(run, user):
    from dynamic_pipeline.services import user_can_act

    run.refresh_from_db()
    return user_can_act(run, user)
