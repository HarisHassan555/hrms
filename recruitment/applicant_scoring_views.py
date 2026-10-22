"""HTTP views for ranked applicant scoring."""

from django.contrib import messages
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_POST

from horilla.decorators import login_required
from recruitment.decorators import manager_can_enter
from recruitment.applicant_scoring import applicants_queryset, rank_applicants
from recruitment.models import Candidate, Recruitment, Stage


@login_required
@manager_can_enter("recruitment.view_recruitment")
def applicant_scoring_panel(request, rec_id):
    recruitment = get_object_or_404(Recruitment.objects.entire(), pk=rec_id)
    ranked = rank_applicants(recruitment)
    stages = Stage.objects.filter(recruitment_id=recruitment).order_by("sequence")
    skill_count = recruitment.skills.count()
    return render(
        request,
        "cbv/pipeline/applicant_scoring_panel.html",
        {
            "recruitment": recruitment,
            "ranked": ranked,
            "stages": stages,
            "skill_count": skill_count,
            "applicant_count": applicants_queryset(recruitment).count(),
            "pipeline_url": reverse(
                "recruitment-pipeline-shell", kwargs={"rec_id": recruitment.pk}
            ),
        },
    )


@login_required
@require_POST
@manager_can_enter("recruitment.change_candidate")
def applicant_scoring_bulk_stage(request, rec_id):
    recruitment = get_object_or_404(Recruitment.objects.entire(), pk=rec_id)
    stage_id = request.POST.get("stage_id")
    candidate_ids = request.POST.getlist("candidate_ids")
    if not stage_id or not candidate_ids:
        messages.error(request, _("Select a stage and at least one applicant."))
        return _scoring_response(request, rec_id)

    stage = get_object_or_404(Stage, pk=stage_id, recruitment_id=recruitment)
    updated = Candidate.objects.filter(
        pk__in=candidate_ids,
        recruitment_id=recruitment,
        source="application",
        stage_id__stage_type="applied",
        canceled=False,
    ).update(stage_id=stage)
    messages.success(
        request,
        _("Moved %(count)s applicant(s) to %(stage)s.")
        % {"count": updated, "stage": stage.stage},
    )
    return _scoring_response(request, rec_id)


def _scoring_response(request, rec_id):
    if request.META.get("HTTP_HX_REQUEST"):
        return applicant_scoring_panel(request, rec_id)
    return HttpResponse(status=204)
