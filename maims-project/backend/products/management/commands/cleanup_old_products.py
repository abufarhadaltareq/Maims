"""Delete products that are older than 30 days.

Run on a schedule (cron / Railway / Render job):

    python manage.py cleanup_old_products

Products are removed from the database; order lines keep a snapshot of the
product name so past receipts stay readable.
"""

import logging

from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta

from products.models import Product

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Delete products older than 30 days.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days', type=int, default=30,
            help='Age threshold in days (default: 30).')
        parser.add_argument(
            '--dry-run', action='store_true',
            help='Report what would be deleted without deleting.')

    def handle(self, *args, **options):
        cutoff = timezone.now() - timedelta(days=options['days'])
        qs = Product.objects.filter(date_added__lt=cutoff)
        count = qs.count()
        if options['dry_run']:
            self.stdout.write(f'would delete {count} product(s) older than {options["days"]} days')
            return
        deleted, _ = qs.delete()
        self.stdout.write(self.style.SUCCESS(f'deleted {deleted} product(s) older than {options["days"]} days'))
        logger.info('cleanup_old_products deleted %s products', deleted)
