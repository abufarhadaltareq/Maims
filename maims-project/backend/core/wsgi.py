"""
WSGI config for core project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/6.0/howto/deployment/wsgi/
"""

import os
import django
from django.core.wsgi import get_wsgi_application
from django.core.management import call_command

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

# Initialize Django apps first, then run migrations safely on startup
try:
    django.setup()
    call_command('migrate', interactive=False)
    print("Database migrations applied successfully on startup.")
except Exception as e:
    print(f"Skipping or error during auto-migration: {e}")

application = get_wsgi_application()