"""Reconcile the catalogue with the Facebook Page feed.

Run from cron (e.g. every 10 minutes):

    python manage.py sync_facebook_catalog

1. Reads the last `--limit` (default 50) posts from /{page-id}/feed.
2. Creates or updates the Product for each post through the same
   code path as the webhook, so the two can never disagree.
3. Reconciliation: synced products whose post is no longer in the
   fetched window are marked sold (stock 0). Only products created
   inside the window are eligible — a post that merely scrolled past
   the 50-post window is not the same as a deleted post.

Flags:
  --dry-run   Log every action without writing.
  --purge     Delete stale synced products instead of marking them
              sold. Products that appear in any order are never
              purged (deleting a Product cascades onto its
              OrderItems and destroys order history); they are marked
              sold instead and reported.
"""

import logging

from django.core.management.base import BaseCommand
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from products import facebook
from products.models import Product

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Sync products from the Facebook Page feed into the catalogue'

    def add_arguments(self, parser):
        parser.add_argument('--limit', type=int, default=50,
                            help='Number of recent posts to read (default: 50)')
        parser.add_argument('--dry-run', action='store_true',
                            help='Preview changes without writing')
        parser.add_argument('--purge', action='store_true',
                            help='Delete stale synced products (only those with no order history)')

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        purge = options['purge']
        limit = max(1, min(options['limit'], 200))

        page_id, token = facebook.get_page_credentials()
        if not page_id or not token:
            self.stderr.write(self.style.ERROR(
                'Facebook sync is not configured. Set FACEBOOK_PAGE_ID and '
                'FACEBOOK_PAGE_ACCESS_TOKEN (environment) or fill them in '
                'Admin → Store settings.'))
            return

        posts = facebook.fetch_page_feed(limit=limit)
        if not posts:
            self.stdout.write(self.style.WARNING('No posts fetched — nothing to sync.'))
            return

        seen_ids = set()
        for post in posts:
            post_id = post.get('id')
            if not post_id:
                continue
            seen_ids.add(post_id)

            if dry_run:
                parsed = facebook.parse_product_post(post.get('message') or '')
                exists = Product.objects.filter(facebook_post_id=post_id).exists()
                self.stdout.write(f"  [{'update' if exists else 'create'}] "
                                  f"{parsed['title'] or '(no title)'}  ({post_id})")
                continue

            facebook.upsert_product_from_post(
                post_id, post.get('message') or '', post.get('full_picture') or '')

        if dry_run:
            self.stdout.write(self.style.SUCCESS(
                f'Dry run: {len(seen_ids)} posts would be synced.'))
            return

        # --- Reconciliation: posts that vanished from the window ---
        created_times = [parse_datetime(p['created_time']) for p in posts
                         if p.get('created_time')]
        created_times = [t for t in created_times if t is not None]
        oldest = min(created_times) if created_times else None

        eligible = Product.objects.filter(facebook_post_id__isnull=False)
        if oldest:
            # A one-day buffer: posts created just before the window
            # edge may legitimately still be on the page.
            eligible = eligible.filter(date_added__gte=oldest - timezone.timedelta(days=1))
        stale = eligible.exclude(facebook_post_id__in=seen_ids)

        purged = sold = with_history = 0
        for product in stale:
            if purge and not product.items.exists():
                product.delete()
                purged += 1
                logger.info('Purged product #%s (Facebook post gone)', product.id)
            else:
                product.stock = 0
                product.save(update_fields=['stock'])
                sold += 1
                if product.items.exists():
                    with_history += 1
                logger.info('Product #%s marked sold (Facebook post gone)', product.id)

        self.stdout.write(self.style.SUCCESS(
            f'Synced {len(seen_ids)} posts; '
            f'{sold} product(s) marked sold'
            + (f' ({with_history} keep order history)' if with_history else '')
            + (f'; {purged} purged' if purged else '') + '.'))
