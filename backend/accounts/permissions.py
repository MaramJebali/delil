from rest_framework.permissions import BasePermission


class IsOfficer(BasePermission):
    """Allows access only to users with role=officer."""

    message = "Officer role required."

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and getattr(request.user, "role", None) == "officer"
        )