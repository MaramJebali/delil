from django.contrib.auth import get_user_model
from rest_framework import generics, status, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from .models import Claim, Evidence, MediationSession
from .permissions import IsOfficer
from .serializers import (
    RegisterSerializer,
    UserSerializer,
    ClaimSerializer,
    EvidenceSerializer,
    MediationSessionSerializer,
)

User = get_user_model()


# ------------------------------------------------------------------
# Auth
# ------------------------------------------------------------------

class RegisterView(generics.CreateAPIView):
    """Public signup (citizens only)."""
    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        refresh = RefreshToken.for_user(user)
        return Response(
            {
                "user": UserSerializer(user).data,
                "access": str(refresh.access_token),
                "refresh": str(refresh),
            },
            status=status.HTTP_201_CREATED,
        )


class MeView(APIView):
    """Return the authenticated user's info."""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        return Response(UserSerializer(request.user).data)


class LoginView(APIView):
    """Simple login → returns user + JWT (no email verification)."""
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        from django.contrib.auth import authenticate

        username = request.data.get("username")
        password = request.data.get("password")

        user = authenticate(username=username, password=password)
        if not user:
            return Response(
                {"detail": "Invalid credentials"},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        refresh = RefreshToken.for_user(user)
        return Response(
            {
                "user": UserSerializer(user).data,
                "access": str(refresh.access_token),
                "refresh": str(refresh),
            }
        )


# ------------------------------------------------------------------
# Citizen: create + list own claims
# ------------------------------------------------------------------

class ClaimListCreateView(generics.ListCreateAPIView):
    serializer_class = ClaimSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Claim.objects.filter(citizen=self.request.user).order_by("-created_at")

    def perform_create(self, serializer):
        serializer.save(citizen=self.request.user)


class ClaimDetailView(generics.RetrieveAPIView):
    serializer_class = ClaimSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Claim.objects.filter(citizen=self.request.user)


# ------------------------------------------------------------------
# Officer endpoints
# ------------------------------------------------------------------

class OfficerClaimListView(generics.ListAPIView):
    queryset = Claim.objects.all().order_by("-created_at")
    serializer_class = ClaimSerializer
    permission_classes = [IsOfficer]


class OfficerClaimDetailView(generics.RetrieveAPIView):
    queryset = Claim.objects.all()
    serializer_class = ClaimSerializer
    permission_classes = [IsOfficer]


class OfficerClaimApproveView(APIView):
    permission_classes = [IsOfficer]

    def post(self, request, pk):
        try:
            claim = Claim.objects.get(pk=pk)
        except Claim.DoesNotExist:
            return Response({"detail": "Not found"}, status=404)

        claim.status = Claim.Status.APPROVED
        claim.officer = request.user
        claim.officer_notes = request.data.get("officer_notes", claim.officer_notes)
        claim.save()
        return Response(ClaimSerializer(claim).data)


class OfficerClaimRejectView(APIView):
    permission_classes = [IsOfficer]

    def post(self, request, pk):
        try:
            claim = Claim.objects.get(pk=pk)
        except Claim.DoesNotExist:
            return Response({"detail": "Not found"}, status=404)

        claim.status = Claim.Status.REJECTED
        claim.officer = request.user
        claim.officer_notes = request.data.get("officer_notes", claim.officer_notes)
        claim.save()
        return Response(ClaimSerializer(claim).data)


class OfficerScheduleMediationView(APIView):
    permission_classes = [IsOfficer]

    def post(self, request, pk):
        try:
            claim = Claim.objects.get(pk=pk)
        except Claim.DoesNotExist:
            return Response({"detail": "Not found"}, status=404)

        scheduled_at = request.data.get("scheduled_at")
        location = request.data.get("location", "")
        notes = request.data.get("notes", "")

        if not scheduled_at:
            return Response(
                {"detail": "scheduled_at is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        mediation, _ = MediationSession.objects.update_or_create(
            claim=claim,
            defaults={
                "officer": request.user,
                "scheduled_at": scheduled_at,
                "location": location,
                "notes": notes,
            },
        )

        claim.status = Claim.Status.SCHEDULED
        claim.officer = request.user
        claim.save()

        return Response(MediationSessionSerializer(mediation).data)