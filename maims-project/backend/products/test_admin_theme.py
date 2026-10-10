"""The admin must serve django-unfold's assets, not Django's stock theme.

Replaces the earlier Jazzmin assertions: Jazzmin was swapped out for Unfold, and
tests that pinned the old assets would pass or fail for the wrong reason. These
tests guard the *current* theme so a future theme change is a deliberate, visible
edit rather than a silent one.
"""

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse


class UnfoldThemeTests(TestCase):
    def setUp(self):
        User.objects.create_superuser('root', 'root@example.com', 'pw12345!Zx')
        self.client.force_login(User.objects.get(username='root'))

    def assert_unfold(self, url):
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200, url)
        html = response.content.decode()

        # Unfold ships its own Tailwind build; it must be the stylesheet in use.
        self.assertIn('unfold/css/styles.css', html)
        # Maims' overrides are injected through UNFOLD["STYLES"] on every page.
        self.assertIn('maims.css', html)
        # Unfold's icon font is what renders the sidebar's Material icons.
        self.assertIn('unfold/fonts/material-symbols/styles.css', html)
        return html

    def test_admin_index_uses_unfold(self):
        html = self.assert_unfold(reverse('admin:index'))
        # The dashboard keeps its order queues and store-data links.
        self.assertIn('maims-home', html)

    def test_changelists_use_unfold(self):
        for name in ('products_order_changelist', 'products_product_changelist',
                     'auth_user_changelist'):
            self.assert_unfold(reverse(f'admin:{name}'))

    def test_admin_sidebar_links_are_configured(self):
        """The sidebar is the shop's map — a broken callback must fail here."""
        html = self.assert_unfold(reverse('admin:index'))
        # Environment callback + dashboard callback are wired in core/admin.py.
        self.assertIn('maims-home', html)
        for label in ('Awaiting our decision', 'Products', 'Categories', 'Store settings'):
            self.assertIn(label, html)
