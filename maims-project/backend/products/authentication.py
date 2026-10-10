"""Authentication classes for the public API."""

import logging

from django.conf import settings
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from rest_framework.authentication import TokenAuthentication
from rest_framework.exceptions import AuthenticationFailed

logger = logging.getLogger(__name__)


class ExpiringTokenAuthentication(TokenAuthentication):
    """DRF token auth that stops accepting tokens after ``AUTH_TOKEN_MAX_AGE_DAYS``.

    ``rest_framework.authtoken`` issues a token whose only invalidation is a
    manual logout or a database delete. A token leaked from localStorage — the
    browser store this frontend uses — therefore works for the lifetime of the
    account, including after the customer changes their password.

    Reusing the stock class keeps every existing behaviour that the API relies on
    (the ``Authorization: Token <key>`` header, the ``user.is_active`` check, the
    ``auth_token`` convenience attribute) and only adds an age check. The limit
    is read per request from settings so deployments can tune or disable it
    without a code change.
    """

    def authenticate(self, request):
        result = super().authenticate(request)
        if result is None:
            return None

        user, token = result

        max_age_days = getattr(settings, 'AUTH_TOKEN_MAX_AGE_DAYS', 0)
        if max_age_days and token.created is not None:
            max_age_seconds = max_age_days * 24 * 60 * 60
            age = (timezone.now() - token.created).total_seconds()
            if age > max_age_seconds:
                # Deleting the token forces a re-login on the frontend: the
                # interceptor sees the 401, clears localStorage and the user
                # signs in again to get a fresh one.
                token.delete()
                logger.info(
                    'Expired token for user %s rejected after %s days',
                    user.pk, max_age_days,
                )
                raise AuthenticationFailed(
                    _('Your session has expired. Please sign in again.')
                )

        return result
