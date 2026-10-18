import re

from django.conf import settings
from django.conf.urls.static import static
from django.urls import include, path, re_path

from core.admin_site import maims_admin
from core.views import health, ping, redirect_root

urlpatterns = [
    path('', redirect_root),
    # The Maims admin site (branding, dashboard, custom order pages) replaces
    # the default admin.site.
    path('admin/', maims_admin.urls),
    path('api/v1/', include('products.urls')),
    # Container/orchestrator probe: unauthenticated, cheap, DB-aware.
    path('health/', health, name='health'),
    path('ping/', ping, name='ping'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
elif settings.SERVE_MEDIA:
    # With DEBUG=False Django stops serving MEDIA_URL, which silently breaks
    # every product photo on a deploy that has no object store attached. Serve
    # the uploads from the app so a fresh production deploy shows real images;
    # set SERVE_MEDIA=False when a CDN/S3 bucket takes over via MEDIA_URL.
    #
    # The route is built by hand rather than with django.conf.urls.static.static()
    # because that helper deliberately returns [] unless DEBUG is True — calling
    # it here would silently register nothing and every image would 404.
    from django.views.static import serve

    urlpatterns += [
        re_path(
            r'^%s(?P<path>.*)$' % re.escape(settings.MEDIA_URL.lstrip('/')),
            serve,
            {'document_root': settings.MEDIA_ROOT},
        ),
    ]
