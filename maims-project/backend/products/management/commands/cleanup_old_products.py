"""Delete expired products and uploaded media no longer referenced by the shop.

Run daily from a scheduler:

    python manage.py cleanup_old_products

The retention period and enabled state are controlled in Admin → Product
retention settings. Order lines retain their product-name snapshot.
"""

import logging
from datetime import timedelta
from urllib.parse import urlsplit

from django.apps import apps
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import FileField
from django.utils import timezone

from products.models import Product, ProductMedia, ProductRetentionSettings

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Delete expired products and their unreferenced uploaded media.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days', type=int, default=None,
            help='Override the retention setting for this run.')
        parser.add_argument(
            '--dry-run', action='store_true',
            help='Report what would be deleted without deleting.')

    def handle(self, *args, **options):
        settings = ProductRetentionSettings.get()
        if not settings.enabled:
            self.stdout.write('Product cleanup is disabled in Product retention settings.')
            return

        days = options['days'] if options['days'] is not None else settings.retention_days
        if days < 1:
            raise CommandError('--days must be at least 1.')

        cutoff = timezone.now() - timedelta(days=days)
        products = Product.objects.filter(date_added__lt=cutoff)
        product_ids = list(products.values_list('pk', flat=True))
        if not product_ids:
            self.stdout.write(f'No products older than {days} days.')
            return

        media_files = self._files_for_products(product_ids)
        unreferenced = self._unreferenced_files(media_files, product_ids)

        if options['dry_run']:
            self.stdout.write(
                f'would delete {len(product_ids)} product(s) older than {days} days '
                f'and remove {len(unreferenced)} unreferenced media file(s)')
            return

        with transaction.atomic():
            deleted, _ = products.delete()

        removed = 0
        failures = []
        for storage, name in unreferenced:
            try:
                storage.delete(name)
                removed += 1
            except Exception:
                logger.exception('Could not delete unreferenced product media %s', name)
                failures.append(name)

        self.stdout.write(self.style.SUCCESS(
            f'deleted {len(product_ids)} product(s) ({deleted} database row(s)); '
            f'removed {removed} unreferenced media file(s) older than {days} days'))
        logger.info(
            'cleanup_old_products deleted %s products and removed %s media files',
            len(product_ids), removed)
        if failures:
            raise CommandError(
                f'Deleted products, but failed to remove {len(failures)} unreferenced media file(s). '
                'See the log for details.')

    @staticmethod
    def _files_for_products(product_ids):
        files = []
        for field_name in ('image', 'thumbnail'):
            field = Product._meta.get_field(field_name)
            for name in Product.objects.filter(pk__in=product_ids).values_list(field_name, flat=True):
                if name:
                    files.append((field.storage, name))

        field = ProductMedia._meta.get_field('file')
        for name in ProductMedia.objects.filter(product_id__in=product_ids).values_list('file', flat=True):
            if name:
                files.append((field.storage, name))
        return files

    @staticmethod
    def _unreferenced_files(files, product_ids):
        groups = []
        for storage, name in files:
            if urlsplit(name).scheme or name.startswith('//'):
                continue
            group = next((entry for entry in groups if entry[0] == storage), None)
            if group is None:
                group = (storage, set())
                groups.append(group)
            group[1].add(name)

        referenced = set()
        for model in apps.get_models():
            for field in model._meta.concrete_fields:
                if not isinstance(field, FileField):
                    continue
                group_index = next(
                    (index for index, (storage, _) in enumerate(groups) if storage == field.storage),
                    None)
                if group_index is None:
                    continue
                names = groups[group_index][1]
                query = model._default_manager.filter(**{f'{field.name}__in': names})
                if model is Product:
                    query = query.exclude(pk__in=product_ids)
                elif model is ProductMedia:
                    query = query.exclude(product_id__in=product_ids)
                referenced.update((group_index, name) for name in query.values_list(field.name, flat=True))

        unreferenced = []
        for index, (storage, names) in enumerate(groups):
            unreferenced.extend((storage, name) for name in names if (index, name) not in referenced)
        return unreferenced
