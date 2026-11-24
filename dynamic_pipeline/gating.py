"""Let an existing approve or reject view share a pipeline run.

When no pipeline is waiting, the caller keeps its old behavior. When the
decision finishes the pipeline, the caller applies its own final side effects
(leave balance, asset allocation). A partial AND step stops here.
"""

from django.contrib import messages
from django.utils.translation import gettext as _

from dynamic_pipeline.models import PipelineRun
from dynamic_pipeline.services import PipelineError, decide, pending_run
from horilla.http.response import HorillaRedirect


def record_for_domain(request, process_code: str, target, decision: str, comment: str = ""):
    """
    Record a decision if a pipeline is waiting.

    Returns a response when the caller must stop, or None when the caller
    should continue with its existing final behavior.
    """
    run = pending_run(process_code, target)
    if run is None:
        return None
    try:
        updated = decide(run, request.user, decision, comment)
    except PipelineError as exc:
        messages.error(request, str(exc))
        return HorillaRedirect(request)
    if decision == "approved" and updated.status == PipelineRun.PENDING:
        messages.success(
            request,
            _(
                "Approval recorded. The request stays open until every required step is complete."
            ),
        )
        return HorillaRedirect(request)
    return None
