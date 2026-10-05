from django.urls import path
from .views import APIKeyDeleteView, APIKeyListCreateView, ChatInputAPIView


urlpatterns = [
    path("message/", ChatInputAPIView.as_view(), name="message-agent"),
    path("api-keys/", APIKeyListCreateView.as_view(), name="api-key-list-create"),
    path("api-keys/<int:pk>/", APIKeyDeleteView.as_view(), name="api-key-delete"),
]