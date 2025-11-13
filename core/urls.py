from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path("admin/", admin.site.urls),
    # Include messaging app URLs under /messages
    path("messages/", include("messaging.urls", namespace="messaging")),
]
