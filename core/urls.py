from django.contrib import admin
from django.urls import path, include
from django.views.generic.base import RedirectView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("messages/", include("messaging.urls", namespace="messaging")),
    path("", RedirectView.as_view(url="/messages/", permanent=False)),
]
