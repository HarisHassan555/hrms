from django.urls import path

from dynamic_pipeline import views

urlpatterns = [
    path("", views.pipeline_list, name="pipeline-list"),
    path("approvals/", views.approval_inbox, name="pipeline-approvals"),
    path("approvals/<int:run_id>/", views.approval_decide, name="pipeline-decide"),
    path("<slug:code>/", views.pipeline_edit, name="pipeline-edit"),
    path("<slug:code>/clear/", views.pipeline_clear, name="pipeline-clear"),
]
