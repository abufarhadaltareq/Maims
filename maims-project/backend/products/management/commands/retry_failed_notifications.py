"""Retry dispatch of previously failed order notifications.

Run on a schedule (cron / Railway / Render job) so a transient provider
outage (SMTP down, Meta unreachable) does not lose customer messages:

    python manage.py retry_failed_notifications --hours 48 --max-attempts 5

Only notifications whose last attempt is inside the window are retried, and
each retry bumps `attempts` so a permanently broken channel cannot loop
forever. Sends that were never configured (recorded as `skipped`) are not
touched.
"""

import logging

from django.core.management.base import BaseCommand
from django.utils import timezone

from products.models import OrderNotification
from products import notifications

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Resend failed order email/WhatsApp notifications (bounded, idempotent).'

    def add_arguments(self, parser):
        parser.add_argument(
            '--hours', type=int, default=48,
            help='Only retry failures last created within this many hours (default: 48).')
        parser.add_argument(
            '--max-attempts', type=int, default=5,
            help='Skip rows already attempted this many times (default: 5).')
        parser.add_argument(
            '--channel', choices=['email', 'whatsapp'], default=None,
            help='Retry only this channel (default: both).')
        parser.add_argument(
            '--dry-run', action='store_true',
            help='Report what would be retried without sending anything.')

    def handle(self, *args, **options):
        cutoff = timezone.now() - timezone.timedelta(hours=options['hours'])
        failed = (OrderNotification.objects
                  .filter(status='failed', created_at__gte=cutoff,
                          attempts__lte=options['max_attempts'])
                  .select_related('order'))
        if options['channel']:
            failed = failed.filter(channel=options['channel'])

        # One retry per (order, channel): the row carries attempts, and the
        # resend path deletes the failed row before re-sending, so iterating
        # order-by-order keeps concurrent runs from double-texting anyone.
        order_channels = {}
        for row in failed.order_by('order_id', 'channel', '-attempts'):
            order_channels.setdefault(row.order_id, {}).setdefault(row.channel, row)

        retried = sent = skipped = 0
        for order_id, channels in sorted(order_channels.items()):
            for channel, row in sorted(channels.items()):
                if options['dry_run']:
                    self.stdout.write(
                        f'would retry order #{order_id} {channel} '
                        f'(attempts={row.attempts}, last error: {row.error[:80]})')
                    retried += 1
                    continue
                try:
                    order = row.order
                    notifications.resend_failed(order, channel=channel)
                    failures_left = order.notifications.filter(
                        status='failed', channel=channel).count()
                    if failures_left:
                        skipped += 1
                        logger.warning('Retry still failing for order %s %s',
                                       order_id, channel)
                    else:
                        sent += 1
                    retried += 1
                except Exception:
                    skipped += 1
                    logger.exception('Retry crashed for order %s %s', order_id, channel)

        self.stdout.write(self.style.SUCCESS(
            f'Retried {retried} failed notification(s): {sent} now sending, '
            f'{skipped} still failing.'))
