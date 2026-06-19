from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from .views import redirect_root

# 🌟 REMOVED: from . import views (This was causing the crash!)

urlpatterns = [
    path('', redirect_root),
    path('admin/', admin.site.urls),
    path('api/v1/', include('products.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)