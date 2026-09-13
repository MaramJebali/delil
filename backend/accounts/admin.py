from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User, Claim, Evidence, MediationSession


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ("id", "username", "email", "role", "is_staff")
    list_filter = ("role", "is_staff")
    fieldsets = UserAdmin.fieldsets + (("Dalil", {"fields": ("role",)}),)
    add_fieldsets = UserAdmin.add_fieldsets + (("Dalil", {"fields": ("role",)}),)


@admin.register(Claim)
class ClaimAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "citizen", "status", "officer", "created_at")
    list_filter = ("status", "dispute_type")
    search_fields = ("title", "description", "citizen__username")


@admin.register(Evidence)
class EvidenceAdmin(admin.ModelAdmin):
    list_display = ("id", "claim", "verified", "uploaded_by", "uploaded_at")
    list_filter = ("verified",)


@admin.register(MediationSession)
class MediationSessionAdmin(admin.ModelAdmin):
    list_display = ("id", "claim", "officer", "scheduled_at", "location")