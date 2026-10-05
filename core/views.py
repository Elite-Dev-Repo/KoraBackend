from core.serializers import UserContextSerializer
from asgiref.sync import async_to_sync
from rest_framework import status
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated, AllowAny
from .models import User
from .serializers import UserSerializer, UserProfileSerializer
from .services import extract_text_from_pdf_bytes, generate_user_information




from dj_rest_auth.registration.views import SocialLoginView
from allauth.socialaccount.providers.google.views import GoogleOAuth2Adapter
from allauth.socialaccount.providers.oauth2.client import OAuth2Client

class GoogleLogin(SocialLoginView):
    adapter_class = GoogleOAuth2Adapter
    # client_class is only needed if you are using specific OAuth2 flows
    client_class = OAuth2Client




class UserCreateView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [AllowAny]

class UserProfileView(generics.RetrieveAPIView):
    queryset = User.objects.select_related("user_info")
    serializer_class = UserProfileSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return User.objects.select_related("user_info").get(id=self.request.user.pk)




class GenerateUserInformation(APIView):
    serializer_class = UserContextSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        personal_context = serializer.validated_data.get("personal_context") or ""
        past_projects = serializer.validated_data.get("past_projects") or ""
        resume_file = serializer.validated_data.get("resume")

        resume_text = ""
        if resume_file:
            if resume_file.size > 10 * 1024 * 1024:
                return Response(
                    {"detail": "Resume file too large. Max 10MB."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            try:
                resume_text = extract_text_from_pdf_bytes(resume_file.read())
            except Exception as exc:
                return Response(
                    {"detail": f"Could not read resume PDF: {exc}"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if not resume_text.strip():
                return Response(
                    {"detail": "Could not extract any text from the resume PDF."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        if not personal_context.strip() and not past_projects.strip() and not resume_text.strip():
            return Response(
                {"detail": "Provide personal context, past projects, or upload a resume PDF."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            async_to_sync(generate_user_information)(
                request.user.id, personal_context, past_projects, resume_text
            )
        except Exception as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_502_BAD_GATEWAY,
            )
        profile = User.objects.select_related("user_info").get(id=request.user.pk)
        return Response(
            {
                "detail": "User profile updated successfully.",
                "profile": UserProfileSerializer(profile).data,
            },
            status=status.HTTP_200_OK,
        )

