from django.urls import path

from .views import (
    RegisterView,
    LoginView,
    MeView,
    ClaimListCreateView,
    ClaimDetailView,
    OfficerClaimListView,
    OfficerClaimDetailView,
    OfficerClaimApproveView,
    OfficerClaimRejectView,
    OfficerScheduleMediationView,
)

urlpatterns = [
    # Auth
    path("register/", RegisterView.as_view(), name="register"),
    path("login/", LoginView.as_view(), name="login"),
    path("me/", MeView.as_view(), name="me"),

    # Citizen claims
    path("claims/", ClaimListCreateView.as_view(), name="claim-list-create"),
    path("claims/<int:pk>/", ClaimDetailView.as_view(), name="claim-detail"),

    # Officer endpoints
    path("officer/claims/", OfficerClaimListView.as_view(), name="officer-claim-list"),
    path("officer/claims/<int:pk>/", OfficerClaimDetailView.as_view(), name="officer-claim-detail"),
    path("officer/claims/<int:pk>/approve/", OfficerClaimApproveView.as_view(), name="officer-claim-approve"),
    path("officer/claims/<int:pk>/reject/", OfficerClaimRejectView.as_view(), name="officer-claim-reject"),
    path("officer/claims/<int:pk>/schedule/", OfficerScheduleMediationView.as_view(), name="officer-claim-schedule"),
]