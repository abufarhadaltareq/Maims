from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse


class JazzminThemeTests(TestCase):
    """The admin must serve jazzmin's assets, not Django's own theme."""

    def setUp(self):
        User.objects.create_superuser('root', 'root@example.com', 'pw12345!Zx')
        self.client.force_login(User.objects.get(username='root'))

    def assert_jazzmin(self, url):
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200, url)
        html = response.content.decode()
        # jazzmin's AdminLTE shell, not Django's own base.css theme.
        self.assertIn('vendor/adminlte/css/adminlte.min.css', html)
        self.assertNotIn('admin/css/nav_sidebar.css', html)
        # The Maims dashboard styles must still load on top of jazzmin.
        self.assertIn('maims.css', html)
        return html

    def test_admin_index_uses_jazzmin(self):
        html = self.assert_jazzmin(reverse('admin:index'))
        # The home page carries the order queues and the store-data links.
        self.assertIn('maims-home', html)
        self.assertIn('Orders to handle', html)
        self.assertIn('Store data', html)

    def test_changelists_use_jazzmin(self):
        for name in ('products_order_changelist', 'products_product_changelist',
                     'auth_user_changelist'):
            self.assert_jazzmin(reverse(f'admin:{name}'))
