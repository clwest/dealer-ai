from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/dealer-ai/", include("dealer_ai.urls")),
]
