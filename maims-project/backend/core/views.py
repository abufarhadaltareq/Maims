"""Project-level views: the root redirect and lightweight liveness probes."""

from django.http import JsonResponse
from django.shortcuts import redirect
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_exempt


def redirect_root(request):
    return redirect('admin/')


@never_cache
@csrf_exempt
def health(request):
    """Unauthenticated liveness probe for Docker, Railway and Render."""
    return JsonResponse({'status': 'ok'})


@never_cache
def ping(request):
    """Ultra-lightweight ping probe."""
    return JsonResponse({'ping': 'pong'})
