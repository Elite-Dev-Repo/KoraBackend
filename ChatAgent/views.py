from asgiref.sync import async_to_sync
from rest_framework import generics, status
from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication
from .authentication import APIKeyHeaderAuthentication
from .models import APIKey
from .serializers import (
    APIKeyCreateSerializer,
    APIKeySerializer,
    ChatInputSerializer,
)
from .services import answer_user_questions




class ChatInputAPIView(APIView):
    serializer_class = ChatInputSerializer
    permission_classes = [IsAuthenticated]
    authentication_class = APIKeyHeaderAuthentication

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            answer = async_to_sync(answer_user_questions)(
                request.user.id, serializer.validated_data["input"]
            )
        except Exception as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_502_BAD_GATEWAY,
            )
        return Response({"response": answer}, status=status.HTTP_200_OK)


class APIKeyListCreateView(generics.ListCreateAPIView):
    """GET lists the caller's keys, POST generates a new one.

    The raw key is returned ONLY in the POST response — it is stored
    as a SHA-256 hash and can never be retrieved again.
    """

    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication, SessionAuthentication]

    def get_queryset(self):
        return APIKey.objects.filter(user=self.request.user).order_by("-created_at")

    def get_serializer_class(self):
        if self.request.method == "POST":
            return APIKeyCreateSerializer
        return APIKeySerializer

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = APIKeySerializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def create(self, request, *args, **kwargs):
        serializer = APIKeyCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        api_key_obj, raw_key = APIKey.generate_key(
            user=request.user, name=serializer.validated_data["name"]
        )
        return Response(
            {**APIKeySerializer(api_key_obj).data, "key": raw_key},
            status=status.HTTP_201_CREATED,
        )


class APIKeyDeleteView(generics.DestroyAPIView):
    """DELETE revokes (deletes) one of the caller's keys."""

    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication, SessionAuthentication]
    serializer_class = APIKeySerializer
    lookup_field = "pk"

    def get_queryset(self):
        return APIKey.objects.filter(user=self.request.user)