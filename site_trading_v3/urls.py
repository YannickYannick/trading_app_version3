from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("trading_app.urls")),
]

# Serve static files during development and production
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
else:
    # In production, static files should be served by the web server (nginx, apache, etc.)
    # But we can still add this for development-like environments
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
