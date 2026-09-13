from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """Custom user with a role flag."""

    class Role(models.TextChoices):
        CITIZEN = "citizen", "Citizen"
        OFFICER = "officer", "Officer"

    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.CITIZEN,
    )

    def is_officer(self) -> bool:
        return self.role == self.Role.OFFICER


# ------------------------------------------------------------------
# Institutional (officer-facing) models
# ------------------------------------------------------------------

class Claim(models.Model):
    """A structured digital claim filed by a citizen (feature 3)."""

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        UNDER_REVIEW = "under_review", "Under review"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"
        SCHEDULED = "scheduled", "Mediation scheduled"

    citizen = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="claims",
    )
    title = models.CharField(max_length=255)
    description = models.TextField()
    dispute_type = models.CharField(max_length=120, blank=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )

    officer = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_claims",
    )
    officer_notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return f"Claim #{self.pk} — {self.title}"


class Evidence(models.Model):
    """Uploaded file evidence attached to a claim."""

    claim = models.ForeignKey(
        Claim,
        on_delete=models.CASCADE,
        related_name="evidence",
    )
    file = models.FileField(upload_to="evidence/")
    description = models.CharField(max_length=255, blank=True)
    uploaded_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name="uploaded_evidence",
    )
    verified = models.BooleanField(default=False)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"Evidence for claim #{self.claim_id}"


class MediationSession(models.Model):
    """Scheduled mediation for an approved claim."""

    claim = models.OneToOneField(
        Claim,
        on_delete=models.CASCADE,
        related_name="mediation",
    )
    officer = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name="mediations",
    )
    scheduled_at = models.DateTimeField()
    location = models.CharField(max_length=255, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"Mediation for claim #{self.claim_id}"