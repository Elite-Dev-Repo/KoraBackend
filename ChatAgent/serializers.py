from rest_framework import serializers
from .models import APIKey


class ChatInputSerializer(serializers.Serializer):
    input = serializers.CharField()
    class Meta:
        fields = ["input"]


class APIKeySerializer(serializers.ModelSerializer):
    """Read-only representation — never exposes key_hash or the raw key."""

    class Meta:
        model = APIKey
        fields = ["id", "name", "prefix", "created_at", "is_active"]
        read_only_fields = ["id", "prefix", "created_at", "is_active"]


class APIKeyCreateSerializer(serializers.Serializer):
    """Input for POST /api-keys/ — only a friendly name is required."""

    name = serializers.CharField(max_length=50)