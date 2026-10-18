"""Project-level views: the root redirect and the platform health probe."""

import logging

from django.db import connections
from django.http import JsonResponse
from django.shortcuts import redirect
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_exempt

logger = logging.getLogger(__name__)


def redirect_root(request):
    return redirect('admin/')


@never_cache
@csrf_exempt
def health(request):
    """Liveness/readiness probe used by Docker, Railway and Render.

    The container healthcheck must be cheap enough to run every few seconds, so
    it deliberately does not touch the catalogue or the ORM models: one
    ``SELECT 1`` against the configured database is the only way to know the app
    can still serve traffic. A database outage is the failure that matters, and
    an endpoint that answers 200 while the DB is down only delays the restart.

    No authentication and no cache headers: a load balancer or orchestrator hits
    this unauthenticated, and a cached "healthy" would outlive the outage.
    """
    database = connections['default']
    try:
        with database.cursor() as cursor:
            cursor.execute('SELECT 1')
            cursor.fetchone()
    except Exception:
        # Never echo the driver's message: it can contain host/port/database
        # names that should not leak through a public probe endpoint.
        logger.exception('Health check failed: database unreachable')
        return JsonResponse({'status': 'unhealthy', 'database': 'down'}, status=503)

    return JsonResponse({'status': 'ok', 'database': 'ok'})


@never_cache
def ping(request):
    """Ultra-lightweight ping probe."""
    return JsonResponse({'ping': 'pong'})
