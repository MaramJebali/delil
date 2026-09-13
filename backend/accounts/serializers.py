from django.contrib.auth import get_user_model
from rest_framework import serializers

from .models import Claim, Evidence, MediationSession

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "username", "email", "first_name", "last_name", "role")
        read_only_fields = ("id", "role")


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=6)

    class Meta:
        model = User
        fields = ("id", "username", "email", "password")

    def create(self, validated_data):
        # Role is always CITIZEN on public signup. Officers are seeded via CLI.
        user = User.objects.create_user(
            username=validated_data["username"],
            email=validated_data.get("email", ""),
            password=validated_data["password"],
            role=User.Role.CITIZEN,
        )
        return user


class EvidenceSerializer(serializers.ModelSerializer):
    uploaded_by_username = serializers.CharField(source="uploaded_by.username", read_only=True)

    class Meta:
        model = Evidence
        fields = (
            "id", "claim", "file", "description",
            "uploaded_by_username", "verified", "uploaded_at",
        )
        read_only_fields = ("id", "uploaded_by_username", "uploaded_at")


class MediationSessionSerializer(serializers.ModelSerializer):
    officer_username = serializers.CharField(source="officer.username", read_only=True)

    class Meta:
        model = MediationSession
        fields = (
            "id", "claim", "officer", "officer_username",
            "scheduled_at", "location", "notes", "created_at",
        )
        read_only_fields = ("id", "officer_username", "created_at")


class ClaimSerializer(serializers.ModelSerializer):
    citizen_username = serializers.CharField(source="citizen.username", read_only=True)
    officer_username = serializers.CharField(source="officer.username", read_only=True)
    evidence = EvidenceSerializer(many=True, read_only=True)
    mediation = MediationSessionSerializer(read_only=True)

    class Meta:
        model = Claim
        fields = (
            "id", "citizen", "citizen_username",
            "title", "description", "dispute_type",
            "status", "officer", "officer_username",
            "officer_notes",
            "evidence", "mediation",
            "created_at", "updated_at",
        )
        read_only_fields = (
            "id", "citizen", "citizen_username",
            "officer", "officer_username",
            "status", "officer_notes",
            "created_at", "updated_at",
        )