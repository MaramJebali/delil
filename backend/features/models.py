from django.conf import settings
from django.db import models


class Analysis(models.Model):
    """Feature 1 — Contract Understanding & Assessment."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                             related_name="analyses")
    document = models.FileField(upload_to="contracts/", blank=True, null=True)
    text_input = models.TextField(blank=True)
    result = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


class Guidance(models.Model):
    """Feature 2 — Workflow Guidance."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                             related_name="guidances")
    question = models.TextField()
    context = models.JSONField(default=dict, blank=True)
    result = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


class Dispute(models.Model):
    """Feature 3 — Dispute Resolution (pre-analysis + link to claim)."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                             related_name="disputes")
    description = models.TextField()
    result = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)