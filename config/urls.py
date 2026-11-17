from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("", include("core.urls")),
    path("users/", include("users.urls")),
    path("bank/", include("banking.urls")),
    path("notifications/", include("notifications.urls")),
    path("activity/", include("activity.urls")),
    path("support/", include("support.urls")),
    path("admin-panel/", include("adminpanel.urls")),
    path("django-admin/", admin.site.urls),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
