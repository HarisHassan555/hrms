"""Approval pipelines that replace a single manager or HR step."""

from django.contrib.auth.models import Group
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _

from base.horilla_company_manager import HorillaCompanyManager
from employee.models import Employee
from horilla.models import HorillaModel

MAX_STEPS = 10


class Process(HorillaModel):
    """A kind of request that can have its own approval pipeline."""

    code = models.SlugField(max_length=64, unique=True)
    name = models.CharField(max_length=120)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ["name"]
        verbose_name = _("Process")
        verbose_name_plural = _("Processes")

    def __str__(self) -> str:
        return self.name


class Pipeline(HorillaModel):
    """The active approval chain for one process in one company."""

    process = models.ForeignKey(
        Process, on_delete=models.CASCADE, related_name="pipelines"
    )
    company = models.ForeignKey(
        "base.Company", on_delete=models.CASCADE, related_name="approval_pipelines"
    )
    name = models.CharField(max_length=120, blank=True)
    objects = HorillaCompanyManager("company")

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["process", "company"],
                condition=models.Q(is_active=True),
                name="one_active_pipeline_per_process_company",
            )
        ]
        ordering = ["process__name", "company_id"]
        verbose_name = _("Pipeline")
        verbose_name_plural = _("Pipelines")

    def __str__(self) -> str:
        label = self.name or self.process.name
        return f"{label} ({self.company})"


class PipelineStep(HorillaModel):
    """One ordered gate. AND needs every slot; OR needs any slot."""

    AND = "and"
    OR = "or"
    MODE_CHOICES = (
        (AND, _("Everyone must approve")),
        (OR, _("Any one approval is enough")),
    )

    pipeline = models.ForeignKey(
        Pipeline, on_delete=models.CASCADE, related_name="steps"
    )
    sequence = models.PositiveSmallIntegerField()
    name = models.CharField(max_length=120, blank=True)
    mode = models.CharField(max_length=8, choices=MODE_CHOICES, default=OR)

    class Meta:
        ordering = ["sequence"]
        constraints = [
            models.UniqueConstraint(
                fields=["pipeline", "sequence"],
                name="unique_pipeline_step_sequence",
            ),
            models.CheckConstraint(
                check=models.Q(sequence__gte=1, sequence__lte=MAX_STEPS),
                name="pipeline_step_sequence_between_1_and_10",
            ),
        ]
        verbose_name = _("Pipeline step")
        verbose_name_plural = _("Pipeline steps")

    def __str__(self) -> str:
        return self.name or f"Step {self.sequence}"

    def clean(self):
        super().clean()
        if self.sequence < 1 or self.sequence > MAX_STEPS:
            raise ValidationError(
                {"sequence": _("A pipeline can have at most %(max)s steps.") % {"max": MAX_STEPS}}
            )


class StepAssignee(HorillaModel):
    """Who can act on a step: a person, a role, or the requester's manager."""

    EMPLOYEE = "employee"
    ROLE = "role"
    REPORTING_MANAGER = "reporting_manager"
    KIND_CHOICES = (
        (EMPLOYEE, _("Specific employee")),
        (ROLE, _("Role")),
        (REPORTING_MANAGER, _("Requester's manager")),
    )

    step = models.ForeignKey(
        PipelineStep, on_delete=models.CASCADE, related_name="assignees"
    )
    kind = models.CharField(max_length=32, choices=KIND_CHOICES)
    employee = models.ForeignKey(
        Employee,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="pipeline_assignments",
    )
    role = models.ForeignKey(
        Group,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="pipeline_assignments",
    )

    class Meta:
        verbose_name = _("Step assignee")
        verbose_name_plural = _("Step assignees")

    def __str__(self) -> str:
        if self.kind == self.EMPLOYEE and self.employee_id:
            return str(self.employee)
        if self.kind == self.ROLE and self.role_id:
            return self.role.name
        return self.get_kind_display()

    def clean(self):
        super().clean()
        if self.kind == self.EMPLOYEE and not self.employee_id:
            raise ValidationError({"employee": _("Choose an employee.")})
        if self.kind == self.ROLE and not self.role_id:
            raise ValidationError({"role": _("Choose a role.")})
        if self.kind == self.REPORTING_MANAGER and (self.employee_id or self.role_id):
            raise ValidationError(
                _("A manager step does not take an employee or a role.")
            )


class PipelineRun(HorillaModel):
    """One request moving through a pipeline. Slots are fixed when it starts."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    STATUS_CHOICES = (
        (PENDING, _("Pending")),
        (APPROVED, _("Approved")),
        (REJECTED, _("Rejected")),
    )

    pipeline = models.ForeignKey(
        Pipeline, on_delete=models.PROTECT, related_name="runs"
    )
    process = models.ForeignKey(
        Process, on_delete=models.PROTECT, related_name="runs"
    )
    company = models.ForeignKey("base.Company", on_delete=models.PROTECT)
    requester = models.ForeignKey(
        Employee, on_delete=models.PROTECT, related_name="pipeline_requests"
    )
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    target = GenericForeignKey("content_type", "object_id")
    status = models.CharField(
        max_length=16, choices=STATUS_CHOICES, default=PENDING
    )
    current_sequence = models.PositiveSmallIntegerField(default=1)
    objects = HorillaCompanyManager("company")

    class Meta:
        indexes = [
            models.Index(fields=["content_type", "object_id", "status"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["content_type", "object_id"],
                condition=models.Q(status="pending"),
                name="one_pending_run_per_request",
            )
        ]
        ordering = ["-id"]
        verbose_name = _("Pipeline run")
        verbose_name_plural = _("Pipeline runs")

    def __str__(self) -> str:
        return f"{self.process.code} #{self.object_id} ({self.status})"


class ApprovalSlot(HorillaModel):
    """A resolved approver slot. Manager slots store the manager at start time."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    SKIPPED = "skipped"
    STATUS_CHOICES = (
        (PENDING, _("Pending")),
        (APPROVED, _("Approved")),
        (REJECTED, _("Rejected")),
        (SKIPPED, _("Skipped")),
    )

    run = models.ForeignKey(
        PipelineRun, on_delete=models.CASCADE, related_name="slots"
    )
    sequence = models.PositiveSmallIntegerField()
    mode = models.CharField(max_length=8, choices=PipelineStep.MODE_CHOICES)
    kind = models.CharField(max_length=32, choices=StepAssignee.KIND_CHOICES)
    employee = models.ForeignKey(
        Employee,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="approval_slots",
    )
    role = models.ForeignKey(
        Group,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="approval_slots",
    )
    status = models.CharField(
        max_length=16, choices=STATUS_CHOICES, default=PENDING
    )
    acted_by = models.ForeignKey(
        Employee,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="pipeline_decisions",
    )
    comment = models.CharField(max_length=255, blank=True)
    acted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["sequence", "id"]
        verbose_name = _("Approval slot")
        verbose_name_plural = _("Approval slots")

    def label(self) -> str:
        if self.kind == StepAssignee.REPORTING_MANAGER:
            if self.employee_id:
                return _("Manager: %(name)s") % {"name": self.employee}
            return _("Requester's manager")
        if self.kind == StepAssignee.ROLE and self.role_id:
            return _("Role: %(name)s") % {"name": self.role.name}
        if self.employee_id:
            return str(self.employee)
        return self.get_kind_display()
