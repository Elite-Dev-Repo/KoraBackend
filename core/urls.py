from django.urls import path
from .views import (
    UserCreateView,
    UserProfileView,
    GenerateUserInformation
)

from .views import GoogleLogin


urlpatterns = [
    path("register/", UserCreateView.as_view(), name="user-list"),
     path('auth/google/', GoogleLogin.as_view(), name='google_login'),
    path("profile/", UserProfileView.as_view(), name="user-detail"),
    path("generate_info/", GenerateUserInformation.as_view(), name="generate-user-information")

]