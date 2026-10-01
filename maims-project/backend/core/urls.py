from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from core.admin_site import maims_admin
from core.views import redirect_root

urlpatterns = [
    path('', redirect_root),
    # The Maims admin site (branding, dashboard, custom order pages) replaces
    # the default admin.site.
    path('admin/', maims_admin.urls),
    path('api/v1/', include('products.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
