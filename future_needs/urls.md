# dealer_ai/urls.py

from django.urls import path
from . import views

urlpatterns = [
    path("chat/start/", views.start_chat),
    path("chat/message/", views.send_chat_message),
    path("leads/", views.create_lead),
]


Main project:
path("api/dealer-ai/", include("dealer_ai.urls")),