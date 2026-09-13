from django.urls import path

from .views import (
    ContractExtractView,
    ContractAnalyzeView,
    ContractAskView,
    DisputeResolveView,
    WorkflowChooseActorView,
    WorkflowDiscussView,
    WorkflowIntroView,
    WorkflowSTTView,
    WorkflowTTSView,
)

urlpatterns = [
    # ── Feature 1 — Contract Understanding ──
    path("contract/extract/", ContractExtractView.as_view(), name="contract-extract"),
    path("contract/analyze/", ContractAnalyzeView.as_view(), name="contract-analyze"),
    path("contract/ask/",     ContractAskView.as_view(),     name="contract-ask"),

    # ── Feature 2 — Workflow Guidance ──
    path("workflow/intro/",        WorkflowIntroView.as_view(),       name="workflow-intro"),
    path("workflow/choose-actor/", WorkflowChooseActorView.as_view(), name="workflow-choose-actor"),
    path("workflow/discuss/",      WorkflowDiscussView.as_view(),     name="workflow-discuss"),
    path("workflow/stt/",          WorkflowSTTView.as_view(),         name="workflow-stt"),
    path("workflow/tts/",          WorkflowTTSView.as_view(),         name="workflow-tts"),

    # ── Feature 3 — Dispute Resolution ──
    path("dispute/resolve/", DisputeResolveView.as_view(), name="dispute-resolve"),
]