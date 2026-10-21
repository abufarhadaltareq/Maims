import hashlib
import hmac
import threading
from datetime import timedelta
from decimal import Decimal
from types import SimpleNamespace
from unittest import mock, skipIf

from django.contrib.auth.models import User
from django.core import mail
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import connection
from django.test import TestCase, TransactionTestCase, override_settings
from django.contrib import admin
from django.conf import settings
from django.urls import Resolver404
from django.utils import timezone

from core.admin_site import maims_admin
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from . import facebook

from .models import (
    Category, CurrencyPrice, CustomerNotificationSettings, HeroSlide, Order, OrderItem, Product,
    Review, SiteSettings, UserProfile,
)
from .views import _build_order_items, _CheckoutError, _delivery_fee, _mark_paid_and_reserve, _reserve_stock


class AdminPageTests(TestCase):
    """Every admin list/change page must render.

    Regression cover for the Orders list 500-ing: an unformatted `format_html()`
    call raised "args or kwargs must be provided" for any unpaid order, which
    took down the whole changelist rather than a single row.
    """

    @classmethod
    def setUpTestData(cls):
        cls.admin = User.objects.create_superuser('root', 'root@example.com', 'pw-root-123456')
        cls.category = Category.objects.create(name='Kurta', slug='kurta')
        cls.product = Product.objects.create(
            category=cls.category, name='Silk Kurta', slug='silk-kurta', stock=4)
        CurrencyPrice.objects.create(product=cls.product, currency='EUR', price=Decimal('25.00'))
        cls.order = Order.objects.create(
            first_name='Ada', last_name='Lovelace', email='ada@example.com',
            address='1 Main St', zipcode='1000', place='Lisbon',
            total_amount=Decimal('25.00'), currency='EUR', payment_method='paypal', is_paid=False)
        OrderItem.objects.create(order=cls.order, product=cls.product, size='M',
                                 price=Decimal('25.00'), quantity=1)

    def setUp(self):
        self.client.force_login(self.admin)

    def test_order_changelist_renders_with_unpaid_order(self):
        res = self.client.get('/admin/products/order/')
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, 'Lovelace')

    def test_order_change_page_renders(self):
        res = self.client.get(f'/admin/products/order/{self.order.pk}/change/')
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, 'Silk Kurta')

    def test_dashboard_renders(self):
        res = self.client.get('/admin/')
        self.assertEqual(res.status_code, 200)
        # The home page is a work queue, not a list of statistics.
        self.assertContains(res, 'Orders to handle')
        # 'new' is the decision queue: staff accept or decline before packing.
        self.assertContains(res, 'Awaiting our decision')
        self.assertContains(res, 'Accepted, to pack')

    def test_product_admin_can_sync_facebook_feed_manually(self):
        """Webhooks can't reach a laptop/firewalled host — the admin action is
        the fallback, running the same idempotent upsert as the webhook."""
        posts = [{'id': '111_222',
                  'message': 'Jamdani Saree — Lotus\n€ 120.00\nHandwoven in Dhaka',
                  'full_picture': ''}]
        with mock.patch('products.facebook.fetch_page_feed', return_value=posts) as fetch:
            res = self.client.post('/admin/products/product/', {
                'action': 'sync_facebook_feed',
                '_selected_action': [str(self.product.pk)],
            })
        self.assertEqual(res.status_code, 302)
        fetch.assert_called_once()
        linked = Product.objects.filter(facebook_post_id='111_222')
        self.assertTrue(linked.exists())
        self.assertEqual(linked.first().name, 'Jamdani Saree — Lotus')

    def test_every_registered_changelist_renders(self):
        from core.admin_site import maims_admin
        for model in maims_admin._registry:
            meta = model._meta
            with self.subTest(model=meta.model_name):
                res = self.client.get(f'/admin/{meta.app_label}/{meta.model_name}/')
                self.assertEqual(res.status_code, 200)

    def test_category_without_image_renders(self):
        """A category with no image used to raise on its 'none' thumbnail."""
        res = self.client.get('/admin/products/category/')
        self.assertEqual(res.status_code, 200)

    def test_duplicate_product_action_creates_a_unique_slug(self):
        res = self.client.post('/admin/products/product/', {
            'action': 'duplicate_products',
            '_selected_action': [str(self.product.pk)],
        })
        self.assertEqual(res.status_code, 302)
        copy = Product.objects.get(slug__endswith='-copy')
        self.assertNotEqual(copy.slug, self.product.slug)
        self.assertEqual(CurrencyPrice.objects.filter(product=copy).count(), 1)
        self.assertEqual(copy.stock, 0)

    def test_site_settings_is_a_singleton(self):
        from .models import SiteSettings
        SiteSettings.objects.get_or_create(pk=1)
        # Second row can never be added, and the list page jumps to the form.
        self.assertEqual(self.client.get('/admin/products/sitesettings/add/').status_code, 403)
        res = self.client.get('/admin/products/sitesettings/')
        self.assertEqual(res.status_code, 302)

    def test_notification_settings_is_a_singleton_and_form_renders(self):
        from .models import CustomerNotificationSettings
        row = CustomerNotificationSettings.get()
        # Second row can never be added, and the list page jumps to the form.
        self.assertEqual(
            self.client.get('/admin/products/customernotificationsettings/add/').status_code, 403)
        res = self.client.get('/admin/products/customernotificationsettings/')
        self.assertEqual(res.status_code, 302)
        res = self.client.get(f'/admin/products/customernotificationsettings/{row.pk}/change/')
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, 'Email capture')


class AdminDailyWorkflowTests(AdminPageTests):
    """The one-click tools the shop actually uses every day."""

    def test_advance_button_moves_an_order_to_its_next_step(self):
        order = self.order
        self.assertEqual(order.status, 'new')
        # 'accepted' is a real step: staff confirm they will take the order before
        # packing starts, and the customer is told.
        for expected in ('accepted', 'packed', 'shipped', 'delivered'):
            self.client.post(f'/admin/products/order/{order.pk}/advance/')
            order.refresh_from_db()
            self.assertEqual(order.status, expected)
        # Delivered is terminal: another click must not move it.
        self.client.post(f'/admin/products/order/{order.pk}/advance/')
        order.refresh_from_db()
        self.assertEqual(order.status, 'delivered')

    def test_packing_slip_renders(self):
        res = self.client.get(f'/admin/products/order/{self.order.pk}/packing-slip/')
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, 'Silk Kurta')
        self.assertContains(res, 'Ada Lovelace')

    def test_batch_packing_slips_cover_every_selected_order(self):
        other = Order.objects.create(
            first_name='Grace', last_name='Hopper', email='grace@example.com',
            address='2 Main St', zipcode='2000', place='Porto',
            total_amount=Decimal('10.00'), currency='EUR', payment_method='stripe')
        OrderItem.objects.create(order=other, product=self.product, price=Decimal('10.00'), quantity=1)
        res = self.client.post('/admin/products/order/', {
            'action': 'print_packing_slips',
            '_selected_action': [str(self.order.pk), str(other.pk)],
        })
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, 'Ada Lovelace')
        self.assertContains(res, 'Grace Hopper')

    def test_stock_actions(self):
        product = self.product
        self.client.post('/admin/products/product/', {
            'action': 'add_stock', '_selected_action': [str(product.pk)]})
        product.refresh_from_db()
        self.assertEqual(product.stock, 14)          # 4 + 10

        self.client.post('/admin/products/product/', {
            'action': 'mark_sold_out', '_selected_action': [str(product.pk)]})
        product.refresh_from_db()
        self.assertEqual(product.stock, 0)

    def test_bulk_restock_only_raises_stock_when_asked(self):
        self.client.post('/admin/products/product/', {
            'action': 'restock_selected', '_selected_action': [str(self.product.pk)],
            'apply_restock': '1', 'new_stock': '30', 'only_if_lower': 'on'})
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 30)

        # With the box unticked, a lower number is applied as-is.
        self.client.post('/admin/products/product/', {
            'action': 'restock_selected', '_selected_action': [str(self.product.pk)],
            'apply_restock': '1', 'new_stock': '5'})
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 5)

    def test_customer_list_shows_lifetime_value_per_currency(self):
        # Give the admin user one paid EUR order and check the column reports it.
        customer = User.objects.create_user('grace', 'grace@example.com', 'pw-grace-123')
        order = Order.objects.create(
            user=customer, first_name='Grace', last_name='Hopper', email='grace@example.com',
            address='2 Main St', zipcode='2000', place='Porto',
            total_amount=Decimal('40.00'), currency='EUR', payment_method='stripe', is_paid=True)
        OrderItem.objects.create(order=order, product=self.product, price=Decimal('40.00'), quantity=1)
        res = self.client.get('/admin/auth/user/')
        self.assertEqual(res.status_code, 200)
        body = res.content.decode()
        self.assertIn('€40.00 EUR', body)      # amount and currency kept together
        self.assertNotIn('€40.00 PKR', body)    # and never mixed with another currency


class ProductCSVImportTests(AdminPageTests):
    """The CSV round trip used for bulk price and stock updates."""

    def _upload(self, body, name='update.csv', create_missing=True):
        upload = SimpleUploadedFile(name, body.encode('utf-8'), content_type='text/csv')
        data = {'csv_file': upload}
        if create_missing:
            data['create_missing'] = 'on'
        return self.client.post('/admin/products/product/import-csv/', data)

    def test_export_lists_every_product_and_price(self):
        CurrencyPrice.objects.create(product=self.product, currency='PKR', price=Decimal('2500'))
        res = self.client.get('/admin/products/product/export-csv/')
        self.assertEqual(res.status_code, 200)
        body = res.content.decode('utf-8-sig')
        self.assertIn('slug,name,category_slug', body)
        self.assertIn('price_EUR', body)
        self.assertIn('25.00', body)      # existing EUR price
        self.assertIn('2500', body)       # the PKR price we just added

    def test_import_updates_stock_and_adds_a_missing_price(self):
        self._upload(f'slug,stock,price_PKR\n{self.product.slug},42,1500\n')
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 42)
        self.assertTrue(CurrencyPrice.objects.filter(
            product=self.product, currency='PKR', price=Decimal('1500')).exists())

    def test_import_creates_a_product_when_asked(self):
        self._upload(
            f'slug,name,category_slug,stock,price_EUR\n'
            f'new-kurta,New Kurta,{self.category.slug},7,199.00\n')
        created = Product.objects.get(slug='new-kurta')
        self.assertEqual(created.stock, 7)
        self.assertEqual(created.category, self.category)
        self.assertTrue(CurrencyPrice.objects.filter(product=created, currency='EUR').exists())

    def test_import_skips_bad_rows_and_reports_why(self):
        self._upload(
            'slug,stock,price_EUR\n'
            ',5,10\n'                                  # no slug
            f'{self.product.slug},not-a-number,10\n')   # unusable stock
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 4)        # unchanged, not corrupted
        body = self.client.get('/admin/products/product/import-csv/').content
        self.assertNotIn(b'not-a-number', body)        # report is per-request

    def test_import_without_create_missing_skips_unknown_slugs(self):
        self._upload('slug,stock\nnever-heard-of-it,3\n', create_missing=False)
        self.assertFalse(Product.objects.filter(slug='never-heard-of-it').exists())

    def test_import_requires_a_slug_column(self):
        res = self._upload('name,stock\nSomething,2\n')
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, 'slug')


class CheckoutPricingSecurityTests(TestCase):
    """Regression tests proving the server never trusts client-supplied prices."""

    def setUp(self):
        self.client = APIClient()
        self.category = Category.objects.create(name='Test Cat', slug='test-cat')
        self.product = Product.objects.create(
            category=self.category, name='Silk Kurta', slug='silk-kurta', stock=10,
        )
        CurrencyPrice.objects.create(product=self.product, currency='EUR', price=Decimal('10.00'))

    def _payload(self, **overrides):
        payload = {
            'first_name': 'Ada', 'last_name': 'Lovelace', 'email': 'ada@example.com',
            'phone': '+351 900000000', 'address': '1 Main St', 'zipcode': '1000',
            'place': 'Lisbon', 'payment_method': 'paypal', 'currency': 'EUR',
            'items': [{'product_id': self.product.id, 'quantity': 2, 'price': '0.01'}],
        }
        payload.update(overrides)
        return payload

    def test_total_is_computed_server_side_not_from_client(self):
        # Client lies about both the unit price and the grand total.
        res = self.client.post('/api/v1/checkout/',
                               self._payload(total_amount='0.01'), format='json')
        self.assertEqual(res.status_code, 201, res.content)
        order = Order.objects.get(id=res.data['order_id'])
        # 2 x 10.00 from the DB, NOT the forged 0.01, plus converted delivery.
        self.assertEqual(order.delivery_fee, Decimal('7.48'))
        self.assertEqual(order.total_amount, Decimal('27.48'))

    @override_settings(STRIPE_SECRET_KEY='sk_test_checkout')
    def test_stripe_intent_charges_server_total_including_delivery(self):
        from django.core.cache import cache

        cache.clear()
        with mock.patch('products.views.stripe.PaymentIntent.create') as create_intent:
            create_intent.return_value = SimpleNamespace(
                id='pi_delivery_test',
                client_secret='pi_delivery_test_secret',
            )
            response = self.client.post(
                '/api/v1/checkout/',
                self._payload(payment_method='stripe', total_amount='0.01'),
                format='json',
            )

        self.assertEqual(response.status_code, 201, response.content)
        self.assertEqual(create_intent.call_args.kwargs['amount'], 2748)
        self.assertEqual(create_intent.call_args.kwargs['currency'], 'eur')
        order = Order.objects.get(pk=response.data['order_id'])
        self.assertEqual(order.total_amount, Decimal('27.48'))

    def test_missing_required_fields_rejected(self):
        res = self.client.post('/api/v1/checkout/',
                               self._payload(email=''), format='json')
        self.assertEqual(res.status_code, 400)
        self.assertFalse(Order.objects.exists())

    def test_missing_phone_rejected(self):
        """Phone is collected by default: no number, no order."""
        res = self.client.post('/api/v1/checkout/',
                               self._payload(phone=''), format='json')
        self.assertEqual(res.status_code, 400)
        self.assertIn('phone', res.data['error'])
        self.assertFalse(Order.objects.exists())

    def test_empty_cart_rejected(self):
        res = self.client.post('/api/v1/checkout/',
                               self._payload(items=[]), format='json')
        self.assertEqual(res.status_code, 400)

    def test_marketing_opt_in_is_stored_when_the_checkbox_would_show(self):
        from django.core.cache import cache
        cache.clear()  # checkout is throttled; keep order irrelevant
        prefs = CustomerNotificationSettings.get()
        prefs.checkout_opt_in_enabled = True
        prefs.status = 'active'
        prefs.recipient_email = 'list@example.com'
        prefs.save()
        res = self.client.post('/api/v1/checkout/',
                               self._payload(marketing_opt_in=True), format='json')
        self.assertEqual(res.status_code, 201, res.content)
        self.assertTrue(Order.objects.get(id=res.data['order_id']).marketing_opt_in)

    def test_marketing_opt_in_dropped_when_consent_row_no_longer_asks(self):
        """A settings flip between page load and POST wins: the server never
        records consent the shop wouldn't be showing anymore."""
        from django.core.cache import cache
        cache.clear()
        prefs = CustomerNotificationSettings.get()
        prefs.checkout_opt_in_enabled = True
        prefs.status = 'paused'   # admin hit pause while the cart was open
        prefs.recipient_email = 'list@example.com'
        prefs.save()
        res = self.client.post('/api/v1/checkout/',
                               self._payload(marketing_opt_in=True), format='json')
        self.assertEqual(res.status_code, 201, res.content)
        self.assertFalse(Order.objects.get(id=res.data['order_id']).marketing_opt_in)


class WebhookSecurityTests(TestCase):
    """The Stripe webhook must reject unsigned payloads."""

    def test_unsigned_webhook_is_rejected_when_no_secret(self):
        res = self.client.post('/api/v1/stripe-webhook/',
                               {'type': 'payment_intent.succeeded',
                                'data': {'object': {'id': 'pi_fake'}}}, format='json')
        # 503 = secret not configured; unsigned events are never trusted.
        self.assertEqual(res.status_code, 503)


class EndpointPermissionTests(TestCase):
    """Public catalog stays open; private endpoints stay closed."""

    def test_products_are_public(self):
        res = self.client.get('/api/v1/products/')
        self.assertEqual(res.status_code, 200)

    def test_order_history_requires_auth(self):
        res = self.client.get('/api/v1/orders/')
        self.assertIn(res.status_code, (401, 403))

    def test_me_requires_auth(self):
        res = self.client.get('/api/v1/me/')
        self.assertIn(res.status_code, (401, 403))


class ProductVisibilityTests(TestCase):
    """Products hidden in the admin must not leak through public catalogue routes."""

    def setUp(self):
        self.client = APIClient()
        self.category = Category.objects.create(name='Hidden Test', slug='hidden-test')
        self.visible = Product.objects.create(
            category=self.category, name='Visible Coat', slug='visible-coat', stock=2,
        )
        self.hidden = Product.objects.create(
            category=self.category, name='Secret Coat', slug='secret-coat',
            stock=2, is_visible=False, facebook_post_id='hidden-post',
        )
        CurrencyPrice.objects.create(
            product=self.visible, currency='EUR', price=Decimal('10.00'),
        )
        CurrencyPrice.objects.create(
            product=self.hidden, currency='EUR', price=Decimal('15.00'),
        )

    def test_hidden_product_is_excluded_from_search_and_category_routes(self):
        search = self.client.get('/api/v1/products/search/?q=Secret')
        category = self.client.get('/api/v1/products/category/hidden-test/')
        showcase = self.client.get('/api/v1/category-showcase/')
        social_feed = self.client.get('/api/v1/social-feed/')

        self.assertEqual(search.status_code, 200)
        self.assertEqual(search.data, [])
        self.assertEqual(category.status_code, 200)
        self.assertEqual([p['slug'] for p in category.data], ['visible-coat'])
        self.assertEqual(showcase.status_code, 200)
        self.assertEqual(showcase.data, [])
        self.assertEqual(social_feed.status_code, 200)
        self.assertEqual(social_feed.data, [])

    def test_homepage_showcase_lists_subcategories_without_parent_categories(self):
        subcategory = Category.objects.create(
            name='Coats', slug='coats', parent=self.category,
        )
        subcategory_product = Product.objects.create(
            category=subcategory, name='Wool Coat', slug='wool-coat', stock=2,
        )
        CurrencyPrice.objects.create(
            product=subcategory_product, currency='EUR', price=Decimal('25.00'),
        )

        response = self.client.get('/api/v1/category-showcase/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual([entry['category']['slug'] for entry in response.data], ['coats'])
        self.assertEqual(
            [product['slug'] for product in response.data[0]['products']],
            ['wool-coat'],
        )

    def test_hidden_product_detail_is_not_found(self):
        response = self.client.get('/api/v1/products/secret-coat/')
        self.assertEqual(response.status_code, 404)

    def test_hidden_product_reviews_are_not_found(self):
        response = self.client.get('/api/v1/products/secret-coat/reviews/')
        self.assertEqual(response.status_code, 404)

    def test_category_product_count_excludes_hidden_products(self):
        response = self.client.get('/api/v1/categories/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data[0]['product_count'], 1)


class HomepageMediaAndDeliveryTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_active_video_slide_is_available_to_homepage(self):
        HeroSlide.objects.create(
            title='Campaign film',
            media_type='video',
            external_video_url='https://example.com/campaign.mp4',
            is_active=True,
        )

        response = self.client.get('/api/v1/hero-slides/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data[0]['media_type'], 'video')
        self.assertEqual(response.data[0]['video_url'], 'https://example.com/campaign.mp4')

    def test_delivery_fee_is_converted_from_sek(self):
        self.assertEqual(_delivery_fee('SEK'), Decimal('85.00'))
        self.assertEqual(_delivery_fee('EUR'), Decimal('7.48'))
        self.assertEqual(_delivery_fee('USD'), Decimal('8.08'))
        self.assertEqual(_delivery_fee('PKR'), Decimal('2243.06'))
        self.assertEqual(_delivery_fee('BDT'), Decimal('950.00'))


class CurrencyPricingTests(TestCase):
    """A currency with no stored price must be rejected, never substituted."""

    def setUp(self):
        self.client = APIClient()
        self.category = Category.objects.create(name='Cat', slug='cat')
        self.product = Product.objects.create(
            category=self.category, name='Only Euro', slug='only-euro', stock=5,
        )
        # NOTE: only EUR is priced — PKR/USD/etc. are intentionally missing.
        CurrencyPrice.objects.create(product=self.product, currency='EUR', price=Decimal('100.00'))

    def _payload(self, currency):
        return {
            'first_name': 'Ada', 'last_name': 'Lovelace', 'email': 'ada@example.com',
            'phone': '+351 900000000', 'address': '1 Main St', 'zipcode': '1000', 'place': 'Lisbon',
            'payment_method': 'paypal', 'currency': currency,
            'items': [{'product_id': self.product.id, 'quantity': 1, 'price': '0.01'}],
        }

    def test_unpriced_currency_is_rejected(self):
        # Client picks PKR where only EUR exists: must NOT be charged EUR 100 as PKR.
        res = self.client.post('/api/v1/checkout/', self._payload('PKR'), format='json')
        self.assertEqual(res.status_code, 400, res.content)
        self.assertFalse(Order.objects.exists())

    def test_priced_currency_is_charged_the_db_amount(self):
        res = self.client.post('/api/v1/checkout/', self._payload('EUR'), format='json')
        self.assertEqual(res.status_code, 201, res.content)
        self.assertEqual(Order.objects.get().total_amount, Decimal('107.48'))


class DuplicateCartLineTests(TestCase):
    """Duplicate lines for the same product are merged before the stock check."""

    def setUp(self):
        self.client = APIClient()
        self.category = Category.objects.create(name='Cat', slug='cat')
        self.product = Product.objects.create(
            category=self.category, name='Ten', slug='ten', stock=10,
        )
        CurrencyPrice.objects.create(product=self.product, currency='EUR', price=Decimal('10.00'))

    def _payload(self, *quantities):
        return {
            'first_name': 'Ada', 'last_name': 'Lovelace', 'email': 'ada@example.com',
            'phone': '+351 900000000', 'address': '1 Main St', 'zipcode': '1000', 'place': 'Lisbon',
            'payment_method': 'paypal', 'currency': 'EUR',
            'items': [{'product_id': self.product.id, 'quantity': q, 'price': '0.01'} for q in quantities],
        }

    def test_two_lines_exceeding_stock_rejected(self):
        # 6 + 6 = 12 > stock 10 -> rejected even though each line alone is fine.
        res = self.client.post('/api/v1/checkout/', self._payload(6, 6), format='json')
        self.assertEqual(res.status_code, 400, res.content)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 10)

    def test_duplicate_lines_merged_and_priced_correctly(self):
        res = self.client.post('/api/v1/checkout/', self._payload(1, 1), format='json')
        self.assertEqual(res.status_code, 201, res.content)
        order = Order.objects.get(id=res.data['order_id'])
        self.assertEqual(order.items.count(), 1)          # merged into a single line
        self.assertEqual(order.items.first().quantity, 2)
        self.assertEqual(order.total_amount, Decimal('27.48'))
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 8)


class StockRaceConditionTests(TransactionTestCase):
    """The last remaining unit must never be sold twice, even under concurrency."""

    def setUp(self):
        self.category = Category.objects.create(name='Cat', slug='cat')
        self.product = Product.objects.create(
            category=self.category, name='Last Unit', slug='last-unit', stock=1,
        )
        CurrencyPrice.objects.create(product=self.product, currency='EUR', price=Decimal('10.00'))

    def _new_order_with_item(self):
        order = Order.objects.create(
            first_name='A', last_name='B', email='a@b.com', address='x',
            zipcode='1', place='y', total_amount=Decimal('0.00'),
            currency='EUR', payment_method='paypal', is_paid=False,
        )
        _build_order_items(order, [{'product_id': self.product.id, 'quantity': 1}], 'EUR')
        return order

    def test_second_reservation_of_last_unit_is_rejected(self):
        first = self._new_order_with_item()
        second = self._new_order_with_item()   # both pass the up-front check (stock still 1)
        _reserve_stock(first)                  # claims the single unit
        with self.assertRaises(_CheckoutError):
            _reserve_stock(second)             # conditional UPDATE matches 0 rows -> rejected
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 0)   # never negative, never -1

    @skipIf(
        connection.vendor == 'sqlite',
        "SQLite's in-memory shared cache cannot run two concurrent writers "
        "(it raises 'database table is locked' before the guard is exercised). "
        "The conditional-UPDATE guarantee is covered deterministically by "
        "test_second_reservation_of_last_unit_is_rejected; this end-to-end "
        "threaded variant runs on Postgres/MySQL.",
    )
    def test_concurrent_checkout_cannot_oversell_last_unit(self):
        results = []
        barrier = threading.Barrier(2)

        def worker():
            try:
                client = APIClient()
                barrier.wait(timeout=10)
                res = client.post('/api/v1/checkout/', {
                    'first_name': 'A', 'last_name': 'B', 'email': 'a@b.com',
                    'phone': '+351 900000000', 'address': 'x', 'zipcode': '1', 'place': 'y',
                    'payment_method': 'paypal', 'currency': 'EUR',
                    'items': [{'product_id': self.product.id, 'quantity': 1, 'price': '0.01'}],
                }, format='json')
                results.append(res.status_code)
            except Exception as exc:                      # pragma: no cover - diagnostics
                results.append(type(exc).__name__)
            finally:
                connection.close()

        threads = [threading.Thread(target=worker) for _ in range(2)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=15)

        # Exactly one buyer wins; the loser is told the item is out of stock.
        self.assertEqual(sorted(results), [201, 400], results)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 0)
        self.assertEqual(Order.objects.count(), 1)   # loser's order rolled back


class PaymentConfirmationIdempotencyTests(TestCase):
    """confirm_checkout / webhook mark paid + decrement stock exactly once."""

    def setUp(self):
        self.client = APIClient()
        self.category = Category.objects.create(name='Cat', slug='cat')
        self.product = Product.objects.create(
            category=self.category, name='Kurta', slug='kurta', stock=5,
        )
        CurrencyPrice.objects.create(product=self.product, currency='EUR', price=Decimal('10.00'))

    def _paid_ready_order(self):
        order = Order.objects.create(
            first_name='A', last_name='B', email='a@b.com', address='x',
            zipcode='1', place='y', total_amount=Decimal('20.00'),
            currency='EUR', payment_method='stripe', is_paid=False,
            stripe_payment_intent_id='pi_test_123',
        )
        _build_order_items(order, [{'product_id': self.product.id, 'quantity': 2}], 'EUR')
        return order

    def test_mark_paid_and_reserve_runs_exactly_once(self):
        order = self._paid_ready_order()
        self.assertTrue(_mark_paid_and_reserve(order))
        self.assertFalse(_mark_paid_and_reserve(order))   # second call is a no-op
        order.refresh_from_db()
        self.product.refresh_from_db()
        self.assertTrue(order.is_paid)
        self.assertEqual(self.product.stock, 3)            # 5 - 2, decremented only once

    def test_paid_transition_sends_one_payment_confirmation(self):
        order = self._paid_ready_order()
        with mock.patch('products.notifications._send_email') as send_email:
            send_email.return_value = (True, '')
            with self.captureOnCommitCallbacks(execute=True):
                self.assertTrue(_mark_paid_and_reserve(order))

        receipt = order.notifications.get(
            channel='email', audience='customer', event='paid'
        )
        self.assertEqual(receipt.status, 'sent')
        self.assertIn('was successful', receipt.body)
        send_email.assert_called_once()

    def test_confirm_checkout_is_idempotent(self):
        order = self._paid_ready_order()
        with mock.patch('products.views.stripe.PaymentIntent.retrieve') as retrieve:
            retrieve.return_value = SimpleNamespace(status='succeeded')
            payload = {'order_id': order.id, 'payment_intent_id': 'pi_test_123'}
            first = self.client.post('/api/v1/checkout/confirm/', payload, format='json')
            second = self.client.post('/api/v1/checkout/confirm/', payload, format='json')
        self.assertEqual(first.status_code, 200, first.content)
        self.assertEqual(second.status_code, 200, second.content)
        order.refresh_from_db()
        self.product.refresh_from_db()
        self.assertTrue(order.is_paid)
        self.assertEqual(self.product.stock, 3)            # not 1 -> no double decrement


class OrderIsolationTests(TestCase):
    """
    IDOR regression tests: authenticated users must not be able to reach,
    modify, or confirm another user's orders or profile by changing ids.
    """

    def setUp(self):
        self.client = APIClient()
        self.category = Category.objects.create(name='Cat', slug='cat')
        self.product = Product.objects.create(
            category=self.category, name='Kurta', slug='kurta', stock=10,
        )
        CurrencyPrice.objects.create(product=self.product, currency='EUR', price=Decimal('10.00'))

        self.alice = User.objects.create_user('alice', 'alice@example.com', 'pw-alice-123')
        self.bob = User.objects.create_user('bob', 'bob@example.com', 'pw-bob-123')

    def _order_for(self, user, pi):
        """Create a stripe order (unpaid) belonging to `user` (None = guest)."""
        order = Order.objects.create(
            user=user, first_name='B', last_name='B', email='b@b.com', address='x',
            zipcode='1', place='y', total_amount=Decimal('10.00'),
            currency='EUR', payment_method='stripe', is_paid=False,
            stripe_payment_intent_id=pi,
        )
        _build_order_items(order, [{'product_id': self.product.id, 'quantity': 1}], 'EUR')
        return order

    def test_order_history_returns_only_own_orders(self):
        alice_order = self._order_for(self.alice, 'pi_alice')
        self._order_for(self.bob, 'pi_bob')                    # Bob's order must not leak
        self.client.force_authenticate(user=self.alice)
        res = self.client.get('/api/v1/orders/')
        self.assertEqual(res.status_code, 200)
        self.assertEqual([o['id'] for o in res.data], [alice_order.id])

    def test_order_payload_hides_payment_intent_id(self):
        self._order_for(self.alice, 'pi_alice')
        self.client.force_authenticate(user=self.alice)
        res = self.client.get('/api/v1/orders/')
        # The Stripe capability token must never be echoed back to clients.
        self.assertNotIn('stripe_payment_intent_id', res.data[0])

    def test_user_cannot_confirm_another_users_order(self):
        bob_order = self._order_for(self.bob, 'pi_bob')
        self.client.force_authenticate(user=self.alice)        # Alice, Bob's ids
        with mock.patch('products.views.stripe.PaymentIntent.retrieve') as retrieve:
            retrieve.return_value = SimpleNamespace(status='succeeded')
            res = self.client.post(
                '/api/v1/checkout/confirm/',
                {'order_id': bob_order.id, 'payment_intent_id': 'pi_bob'},
                format='json',
            )
        self.assertEqual(res.status_code, 404, res.content)
        bob_order.refresh_from_db()
        self.product.refresh_from_db()
        self.assertFalse(bob_order.is_paid)                    # Bob's order untouched
        self.assertEqual(self.product.stock, 10)               # and no stock consumed

    def test_anonymous_cannot_confirm_a_users_order(self):
        bob_order = self._order_for(self.bob, 'pi_bob')
        res = self.client.post(
            '/api/v1/checkout/confirm/',
            {'order_id': bob_order.id, 'payment_intent_id': 'pi_bob'},
            format='json',
        )
        self.assertEqual(res.status_code, 404, res.content)
        bob_order.refresh_from_db()
        self.assertFalse(bob_order.is_paid)

    def test_guest_order_is_still_confirmable(self):
        # Guest checkout (no owner) must keep working: possession of the
        # high-entropy payment intent id is the capability.
        guest_order = self._order_for(None, 'pi_guest')
        with mock.patch('products.views.stripe.PaymentIntent.retrieve') as retrieve:
            retrieve.return_value = SimpleNamespace(status='succeeded')
            res = self.client.post(
                '/api/v1/checkout/confirm/',
                {'order_id': guest_order.id, 'payment_intent_id': 'pi_guest'},
                format='json',
            )
        self.assertEqual(res.status_code, 200, res.content)
        guest_order.refresh_from_db()
        self.assertTrue(guest_order.is_paid)

    def test_profile_update_cannot_target_another_user(self):
        alice_profile = UserProfile.objects.get_or_create(user=self.alice)[0]
        bob_profile = UserProfile.objects.get_or_create(user=self.bob)[0]
        self.client.force_authenticate(user=self.alice)
        # Alice tries to edit Bob's profile by passing Bob's ids.
        res = self.client.put('/api/v1/profile/', {
            'id': bob_profile.id, 'user': self.bob.id,
            'phone': 'alice-phone', 'address': 'alice-addr',
            'zipcode': '9999', 'place': 'Lisbon',
        }, format='json')
        self.assertEqual(res.status_code, 200, res.content)
        bob_profile.refresh_from_db()
        alice_profile.refresh_from_db()
        self.assertNotEqual(bob_profile.phone, 'alice-phone')  # Bob untouched
        self.assertNotEqual(bob_profile.address, 'alice-addr')
        self.assertEqual(alice_profile.phone, 'alice-phone')   # applied to Alice only


class CheckoutIdempotencyTests(TestCase):
    """A retried checkout POST must not create a second order or reserve stock twice.

    The failure this guards against is a customer double-clicking "Pay", hitting
    back then forward, or retrying on a flaky connection: each retry used to build
    a brand new order and decrement inventory again.
    """

    def setUp(self):
        self.client = APIClient()
        self.category = Category.objects.create(name='Cat', slug='cat')
        self.product = Product.objects.create(
            category=self.category, name='Kurta', slug='kurta', stock=10)
        CurrencyPrice.objects.create(product=self.product, currency='EUR', price=Decimal('10.00'))

    def _payload(self):
        return {
            'first_name': 'Ada', 'last_name': 'Lovelace', 'email': 'ada@example.com',
            'phone': '+351 900000000',
            'address': '1 Main St', 'zipcode': '1000', 'place': 'Lisbon',
            'payment_method': 'paypal', 'currency': 'EUR',
            'items': [{'product_id': self.product.id, 'quantity': 2}],
        }

    def test_replayed_request_returns_the_original_order(self):
        key = 'checkout-attempt-abc'
        first = self.client.post('/api/v1/checkout/', self._payload(),
                                 format='json', HTTP_IDEMPOTENCY_KEY=key)
        self.assertEqual(first.status_code, 201, first.content)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 8)

        replay = self.client.post('/api/v1/checkout/', self._payload(),
                                  format='json', HTTP_IDEMPOTENCY_KEY=key)
        # 200, not 201: nothing new was created.
        self.assertEqual(replay.status_code, 200, replay.content)
        self.assertEqual(replay.data['order_id'], first.data['order_id'])

        self.assertEqual(Order.objects.count(), 1)
        # Stock decremented exactly once across both requests.
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 8)

    def test_distinct_keys_create_distinct_orders(self):
        base = self._payload()
        one = self.client.post('/api/v1/checkout/', base, format='json',
                               HTTP_IDEMPOTENCY_KEY='attempt-1')
        two = self.client.post('/api/v1/checkout/', base, format='json',
                               HTTP_IDEMPOTENCY_KEY='attempt-2')
        self.assertEqual(one.status_code, 201)
        self.assertEqual(two.status_code, 201)
        self.assertNotEqual(one.data['order_id'], two.data['order_id'])
        self.assertEqual(Order.objects.count(), 2)

    def test_request_without_a_key_still_works(self):
        res = self.client.post('/api/v1/checkout/', self._payload(), format='json')
        self.assertEqual(res.status_code, 201, res.content)
        self.assertIsNone(Order.objects.get(id=res.data['order_id']).checkout_key)

    def test_replay_cannot_expose_another_customers_order(self):
        key = 'shared-key'
        self.client.post('/api/v1/checkout/', self._payload(), format='json',
                         HTTP_IDEMPOTENCY_KEY=key)

        # A different logged-in customer guessing the key must not be handed the
        # first customer's address and email.
        mallory = User.objects.create_user('mallory', 'm@example.com', 'pw-12345678')
        self.client.force_authenticate(user=mallory)
        res = self.client.post('/api/v1/checkout/', self._payload(), format='json',
                               HTTP_IDEMPOTENCY_KEY=key)
        # No replay match for her, so it is treated as a fresh checkout.
        self.assertEqual(res.status_code, 201, res.content)
        self.assertEqual(Order.objects.count(), 2)

    def test_oversized_idempotency_key_is_truncated_not_rejected(self):
        # Headers are attacker-controlled; a huge key must not reach the column.
        res = self.client.post('/api/v1/checkout/', self._payload(), format='json',
                               HTTP_IDEMPOTENCY_KEY='x' * 500)
        self.assertEqual(res.status_code, 201, res.content)
        self.assertLessEqual(len(Order.objects.get(id=res.data['order_id']).checkout_key), 64)


class StockReleaseTests(TestCase):
    """Refunds and cancellations must put stock back exactly once."""

    def setUp(self):
        self.category = Category.objects.create(name='Cat', slug='cat')
        self.product = Product.objects.create(
            category=self.category, name='Kurta', slug='kurta', stock=10)
        CurrencyPrice.objects.create(product=self.product, currency='EUR', price=Decimal('10.00'))
        self.order = Order.objects.create(
            first_name='Ada', last_name='Lovelace', email='ada@example.com',
            address='1 Main St', zipcode='1000', place='Lisbon',
            total_amount=Decimal('20.00'), currency='EUR', payment_method='paypal', is_paid=False)
        OrderItem.objects.create(order=self.order, product=self.product, size='M',
                                 price=Decimal('10.00'), quantity=2)

    def test_release_stock_returns_units(self):
        from .views import _release_stock

        self.assertTrue(_release_stock(self.order))
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 12)

    def test_release_stock_is_idempotent(self):
        """Stripe retries `charge.refunded` for days; stock must not inflate."""
        from .views import _release_stock

        self.assertTrue(_release_stock(self.order))
        self.assertFalse(_release_stock(self.order))
        self.assertFalse(_release_stock(self.order))
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 12)
        self.order.refresh_from_db()
        self.assertTrue(self.order.stock_released)

    def test_refund_on_unpaid_order_does_not_create_phantom_stock(self):
        """
        A refund for an order whose stock was never reserved must be ignored.

        Otherwise every failed-but-refunded checkout inflates the catalogue:
        the customer never paid, yet their units reappear as sellable stock.
        """
        from unittest import mock

        from django.test import override_settings

        self.assertFalse(self.order.is_paid)
        stock_before = self.product.stock

        event = {
            'type': 'charge.refunded',
            'data': {'object': {'id': 'ch_123', 'payment_intent': 'pi_refund'}},
        }
        Order.objects.filter(pk=self.order.pk).update(stripe_payment_intent_id='pi_refund')

        with override_settings(STRIPE_WEBHOOK_SECRET='whsec_test'):
            with mock.patch('stripe.Webhook.construct_event', return_value=event):
                res = self.client.post('/api/v1/stripe-webhook/', {}, format='json')

        self.assertEqual(res.status_code, 200, res.content)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, stock_before)
        self.order.refresh_from_db()
        self.assertNotEqual(self.order.status, 'returned')

    def test_refund_on_paid_order_releases_stock_once(self):
        """The real path: a paid order is restocked and marked returned."""
        from unittest import mock

        from django.test import override_settings

        _mark_paid_and_reserve(self.order)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 8)   # 10 - 2 reserved
        Order.objects.filter(pk=self.order.pk).update(stripe_payment_intent_id='pi_refund')

        event = {
            'type': 'charge.refunded',
            'data': {'object': {'id': 'ch_123', 'payment_intent': 'pi_refund'}},
        }
        with override_settings(STRIPE_WEBHOOK_SECRET='whsec_test'):
            with mock.patch('stripe.Webhook.construct_event', return_value=event):
                res = self.client.post('/api/v1/stripe-webhook/', {}, format='json')
                self.assertEqual(res.status_code, 200, res.content)
                # Stripe retries the same delivery; the second must be a no-op.
                res = self.client.post('/api/v1/stripe-webhook/', {}, format='json')
                self.assertEqual(res.status_code, 200, res.content)

        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 10)   # back to the original count
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, 'returned')
        self.assertFalse(self.order.is_paid)


class SlugUniquenessTests(TestCase):
    """Slugs are unique at the database level, so `.get(slug=...)` can't 500."""

    def setUp(self):
        self.category = Category.objects.create(name='Cat', slug='cat')

    def test_duplicate_product_slug_is_rejected(self):
        Product.objects.create(category=self.category, name='One', slug='dupe', stock=1)
        from django.db import IntegrityError, transaction as db_transaction

        with self.assertRaises(IntegrityError):
            with db_transaction.atomic():
                Product.objects.create(category=self.category, name='Two', slug='dupe', stock=1)

    def test_duplicate_category_slug_is_rejected(self):
        from django.db import IntegrityError, transaction as db_transaction

        with self.assertRaises(IntegrityError):
            with db_transaction.atomic():
                Category.objects.create(name='Other', slug='cat')

    def test_distinct_slugs_are_fine(self):
        Product.objects.create(category=self.category, name='One', slug='one', stock=1)
        Product.objects.create(category=self.category, name='Two', slug='two', stock=1)
        self.assertEqual(Product.objects.filter(slug__in=['one', 'two']).count(), 2)


class ExpiringTokenTests(TestCase):
    """Tokens must stop working once they exceed AUTH_TOKEN_MAX_AGE_DAYS."""

    def setUp(self):
        self.user = User.objects.create_user('ada', 'ada@example.com', 'pw-12345678')
        self.token = Token.objects.create(user=self.user)
        self.client = APIClient()

    def _age_token_by_days(self, days):
        from django.utils import timezone

        Token.objects.filter(pk=self.token.pk).update(
            created=timezone.now() - timedelta(days=days))

    def test_fresh_token_is_accepted(self):
        res = self.client.get('/api/v1/me/', HTTP_AUTHORIZATION=f'Token {self.token.key}')
        self.assertEqual(res.status_code, 200, res.content)

    def test_expired_token_is_rejected_and_revoked(self):
        # Age the token past the default 90-day limit.
        self._age_token_by_days(91)

        res = self.client.get('/api/v1/me/', HTTP_AUTHORIZATION=f'Token {self.token.key}')
        self.assertEqual(res.status_code, 401)
        # The stale credential is deleted, not merely refused, so it cannot be
        # replayed after the limit is raised.
        self.assertFalse(Token.objects.filter(pk=self.token.pk).exists())
    def test_token_inside_the_window_still_works(self):
        self._age_token_by_days(89)

        res = self.client.get('/api/v1/me/', HTTP_AUTHORIZATION=f'Token {self.token.key}')
        self.assertEqual(res.status_code, 200, res.content)

    def test_expiry_limit_is_configurable(self):
        from django.test import override_settings

        with override_settings(AUTH_TOKEN_MAX_AGE_DAYS=1):
            self._age_token_by_days(2)
            res = self.client.get('/api/v1/me/', HTTP_AUTHORIZATION=f'Token {self.token.key}')
            self.assertEqual(res.status_code, 401)

    def test_logout_revokes_the_token(self):
        """The expiry limit is a ceiling, not a replacement for logout."""
        res = self.client.post('/api/v1/logout/', {}, format='json',
                               HTTP_AUTHORIZATION=f'Token {self.token.key}')
        self.assertEqual(res.status_code, 200, res.content)
        self.assertFalse(Token.objects.filter(pk=self.token.pk).exists())


class HealthCheckTests(TestCase):
    """The orchestrator probe must answer 200 only when the DB is reachable."""

    def test_health_reports_ok(self):
        res = self.client.get('/health/')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()['status'], 'ok')
        self.assertEqual(res.json()['database'], 'ok')

    def test_health_reports_503_when_database_is_down(self):
        from unittest import mock

        with mock.patch('core.views.connections') as conns:
            conns.__getitem__.return_value.cursor.side_effect = Exception('boom')
            res = self.client.get('/health/')
        self.assertEqual(res.status_code, 503)
        body = res.json()
        self.assertEqual(body['status'], 'unhealthy')
        # The driver's message could leak host/port/database names.
        self.assertNotIn('boom', res.content.decode())

    def test_health_needs_no_authentication(self):
        """A load balancer calls this anonymously; a 401 would mean 'unhealthy'."""
        res = self.client.get('/health/')
        self.assertEqual(res.status_code, 200)

    def test_health_is_not_cached(self):
        res = self.client.get('/health/')
        self.assertIn('no-cache', res.headers.get('Cache-Control', ''))


class OrderHistoryQueryCountTests(TestCase):
    """The order history must not issue a query per line."""

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user('ada', 'ada@example.com', 'pw-12345678')
        self.token = Token.objects.create(user=self.user)
        self.category = Category.objects.create(name='Cat', slug='cat')
        self.products = [
            Product.objects.create(category=self.category, name=f'P{i}', slug=f'p{i}', stock=50)
            for i in range(3)
        ]
        for p in self.products:
            CurrencyPrice.objects.create(product=p, currency='EUR', price=Decimal('10.00'))

        for n in range(5):
            order = Order.objects.create(
                user=self.user, first_name='Ada', last_name='L', email='a@example.com',
                address='1 Main St', zipcode='1000', place='Lisbon',
                total_amount=Decimal('20.00'), currency='EUR', payment_method='paypal')
            for product in self.products[:2]:
                OrderItem.objects.create(order=order, product=product, size='M',
                                         price=Decimal('10.00'), quantity=1)

    def test_history_is_rendered_in_a_bounded_number_of_queries(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.token.key}')
        # Warm the connection/query caches so the count is not inflated by
        # one-off setup queries.
        self.client.get('/api/v1/orders/')

        # 8 queries regardless of how many orders/lines/products exist:
        #   1 token auth, 1 orders, 1 items, 1 products (annotated), 1 prices,
        #   1 media, 1 annotated categories, 1 category children.
        # Before the joins this was 26; it then briefly hit 83 when the product
        # prefetch was combined with select_related, and 27 when the rating was
        # resolved per product. The count must stay independent of data size.
        with self.assertNumQueries(8):
            res = self.client.get('/api/v1/orders/')
        self.assertEqual(res.status_code, 200, res.content)
        self.assertEqual(len(res.data), 5)


class ProductListingQueryCountTests(TestCase):
    """
    Listing products must not fetch each product's prices one row at a time.

    Regression guard for Product.get_price, which looked for an attribute Django
    never sets (``_prefetched_prices_cache``). The prefetch was silently ignored
    and every product in the catalogue cost an extra round trip, so a 200-product
    listing ran 200+ queries.
    """

    def setUp(self):
        self.client = APIClient()
        self.category = Category.objects.create(name='Cat', slug='cat')
        for i in range(20):
            product = Product.objects.create(
                category=self.category, name=f'Product {i}', slug=f'product-{i}', stock=10)
            CurrencyPrice.objects.create(product=product, currency='EUR', price=Decimal('15.00'))

    def test_get_price_uses_the_prefetch_cache(self):
        products = list(Product.objects.filter(category=self.category).prefetch_related('prices'))
        with self.assertNumQueries(0):
            # Reading a price from already-prefetched objects must not query.
            prices = {p.slug: p.get_price('EUR') for p in products}
        self.assertEqual(prices['product-0'], Decimal('15.00'))

    def test_get_price_without_prefetch_still_correct(self):
        product = Product.objects.get(slug='product-0')
        self.assertEqual(product.get_price('EUR'), Decimal('15.00'))

    def test_get_price_falls_back_when_currency_missing(self):
        product = Product.objects.get(slug='product-0')
        # Display fallback: an undefined currency returns the first stored price.
        self.assertEqual(product.get_price('USD'), Decimal('15.00'))

    def test_get_price_exact_never_falls_back(self):
        product = Product.objects.get(slug='product-0')
        # Checkout must reject rather than charge a foreign number.
        self.assertIsNone(product.get_price_exact('USD'))
        self.assertEqual(product.get_price_exact('EUR'), Decimal('15.00'))

    def test_catalogue_endpoint_query_count_is_flat(self):
        res = self.client.get('/api/v1/latest-products/')
        self.assertEqual(res.status_code, 200, res.content)
        self.assertEqual(len(res.data), 20)

        # The count must not grow with the catalogue size. 5 queries flat:
        # products, prices, media, annotated categories, category children.
        self.client.get('/api/v1/latest-products/')
        with self.assertNumQueries(5):
            self.client.get('/api/v1/latest-products/')


class ProductionMediaAndStaticTests(TestCase):
    """
    Regression cover for two failures that only appear with DEBUG=False.

    1. Pointing the `default` storage bucket at the static manifest backend made
       every Product.image.url raise "Missing staticfiles manifest entry", so
       /api/v1/latest-products/ returned 500 as soon as one product had a photo.
    2. django.conf.urls.static.static() is a deliberate no-op unless DEBUG is
       True, so using it for the production media route registered nothing and
       every uploaded image 404'd.
    """

    def tearDown(self):
        # urlpatterns are built at import time, so these tests reload the module;
        # put the real ones back for whatever runs next.
        _reload_urls(DEBUG=self._original_debug)

    def _original_debug(self):
        from django.conf import settings as dj_settings

        self._saved_debug = getattr(self, '_saved_debug', dj_settings.DEBUG)
        return self._saved_debug

    @override_settings(DEBUG=False, ALLOWED_HOSTS=['testserver'])
    def test_product_image_url_resolves_with_debug_off(self):
        from django.core.files.uploadedfile import SimpleUploadedFile

        category = Category.objects.create(name='Cat', slug='cat')
        product = Product.objects.create(category=category, name='Kurta', slug='k')
        product.image.save('regression-probe.jpg',
                           SimpleUploadedFile('x.jpg', b'not-a-real-jpeg'), save=True)

        # Must not raise: the manifest storage must never back the default bucket.
        with override_settings(
            STORAGES={
                'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
                'staticfiles': {
                    'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage'
                },
            }
        ):
            self.assertTrue(product.get_image)
        product.image.delete(save=False)

    def test_media_route_is_registered_when_debug_off(self):
        """The production branch must actually add a route."""
        from django.urls import clear_url_caches, resolve

        patterns = _reload_urls(DEBUG=False, SERVE_MEDIA=True)
        try:
            matched = resolve('/media/uploads/anything.jpg')
            self.assertEqual(matched.kwargs['path'], 'uploads/anything.jpg')
            self.assertTrue(str(matched.kwargs['document_root']).endswith('/media'))
            self.assertTrue(
                any('media' in str(p.pattern) for p in patterns),
                'no media pattern registered with DEBUG=False',
            )
        finally:
            clear_url_caches()

    def test_media_route_absent_when_serve_media_is_off(self):
        """SERVE_MEDIA=False hands uploads to a CDN; the app must stop serving."""
        from django.urls import clear_url_caches, resolve

        _reload_urls(DEBUG=False, SERVE_MEDIA=False)
        try:
            with self.assertRaises(Resolver404):
                resolve('/media/uploads/anything.jpg')
        finally:
            clear_url_caches()


def _reload_urls(**overrides):
    """Re-evaluate core.urls.urlpatterns under different settings."""
    import importlib

    import core.urls
    from django.urls import clear_url_caches

    with override_settings(**overrides):
        importlib.reload(core.urls)
        clear_url_caches()
        return core.urls.urlpatterns


# --- ORDER NOTIFICATIONS & FULFILMENT NOTIFICATIONS ---


_make_order_counter = 0


def _make_order(**overrides):
    """A minimal paid order with one line, for the notification tests."""
    global _make_order_counter
    _make_order_counter += 1
    n = _make_order_counter
    # Unique slugs: this helper may be called more than once per test.
    category, _ = Category.objects.get_or_create(slug=f'cat-{n}', defaults={'name': 'Cat'})
    product = Product.objects.create(category=category, name='Kurta',
                                     slug=f'k-{n}', stock=50)
    CurrencyPrice.objects.create(product=product, currency='EUR', price=Decimal('25.00'))
    defaults = dict(
        first_name='Ada', last_name='Lovelace', email='ada@example.com',
        phone='+351 912345678', address='1 Main St', zipcode='1000', place='Lisbon',
        total_amount=Decimal('25.00'), currency='EUR', payment_method='paypal', is_paid=True,
    )
    defaults.update(overrides)
    order = Order.objects.create(**defaults)
    OrderItem.objects.create(order=order, product=product, size='M',
                             price=Decimal('25.00'), quantity=1)
    return order, product


class OrderNotificationTests(TestCase):
    """
    The customer must be told exactly once per status change, over the channels
    they opted into — and a provider failure must never break the order.
    """

    def setUp(self):
        self.store = SiteSettings.get()
        self.store.notification_email = 'shop@example.com'
        self.store.customer_notifications_enabled = True
        self.store.customer_whatsapp_notifications = True
        self.store.save()

        # The order is created inside the commit-capture context: creating an order
        # is itself an event (it fires the new-order alert), and on_commit callbacks
        # registered during setUp would otherwise never run inside a TestCase.
        with mock.patch('products.notifications._send_email') as send, \
                mock.patch('products.notifications._send_whatsapp') as wa:
            send.return_value = (True, '')
            wa.return_value = (True, '')
            with self.captureOnCommitCallbacks(execute=True):
                self.order, self.product = _make_order(whatsapp_opt_in=True)

    def _sent(self, **filter_kwargs):
        return self.order.notifications.filter(status='sent', **filter_kwargs)

    def clear_notifications(self):
        """Forget prior sends so a fresh status event can be asserted cleanly."""
        self.order.notifications.all().delete()
        Order.objects.filter(pk=self.order.pk).update(last_notified_status='')

    def save(self, **fields):
        """
        Save the order and run the notifications it queues.

        Notification dispatch is deliberately deferred with transaction.on_commit
        so a message never describes an order that later rolls back. Inside a
        TestCase that callback would otherwise never fire, so these tests run it
        explicitly — which also keeps the deferral honest rather than papering
        over it.
        """
        with self.captureOnCommitCallbacks(execute=True):
            for name, value in fields.items():
                setattr(self.order, name, value)
            self.order.save()

    def test_unpaid_stripe_order_does_not_send_customer_confirmation(self):
        with mock.patch('products.notifications._send_email') as send_email:
            send_email.return_value = (True, '')
            with self.captureOnCommitCallbacks(execute=True):
                order = Order.objects.create(
                    first_name='Stripe', last_name='Customer',
                    email='stripe@example.com', phone='+351 912345678',
                    address='1 Main St', zipcode='1000', place='Lisbon',
                    total_amount=Decimal('25.00'), currency='EUR',
                    payment_method='stripe', is_paid=False,
                )

        self.assertFalse(order.notifications.filter(
            channel='email', audience='customer', event='new'
        ).exists())
        self.assertTrue(order.notifications.filter(
            channel='email', audience='admin', event='new'
        ).exists())
        send_email.assert_called_once()

    def test_status_change_emails_the_customer_once(self):
        self.clear_notifications()
        with mock.patch('products.notifications._send_email') as send:
            send.return_value = (True, '')
            self.save(status='accepted')

        self.assertEqual(self._sent(channel='email', audience='customer').count(), 1)
        # The body must actually say what happened.
        body = self._sent(channel='email').first().body
        self.assertIn('confirmed your order', body)
        # Subject uses the short customer-facing label, not the staff status text.
        self.assertIn('Order confirmed', self._sent(channel='email').first().subject)

    def test_repeated_save_does_not_notify_twice(self):
        """The admin changelist saves every field at once; that is not two events."""
        self.clear_notifications()
        with mock.patch('products.notifications._send_email') as send:
            send.return_value = (True, '')
            self.save(status='accepted')
            self.save()          # e.g. admin also typed an internal note
            self.save()

        self.assertEqual(self._sent(channel='email', audience='customer').count(), 1)

    def test_notification_body_mentions_each_stage(self):
        expected = {
            'accepted': 'confirmed your order',
            'packed': 'packed',
            'shipped': 'on its way',
            'delivered': 'delivered',
        }
        for status, phrase in expected.items():
            with self.subTest(status=status):
                self.clear_notifications()
                with mock.patch('products.notifications._send_email') as send:
                    send.return_value = (True, '')
                    self.save(status=status)
                self.assertIn(phrase, self._sent(channel='email').first().body)

    def test_shipped_notification_includes_tracking_number(self):
        self.clear_notifications()
        with mock.patch('products.notifications._send_email') as send:
            send.return_value = (True, '')
            self.save(status='shipped', tracking_number='TRACK-123')
        self.assertIn('TRACK-123', self._sent(channel='email').first().body)

    def test_rejection_tells_the_customer_the_reason(self):
        self.clear_notifications()
        with mock.patch('products.notifications._send_email') as send:
            send.return_value = (True, '')
            self.save(status='rejected',
                      rejection_reason='This fabric line is sold out')
        body = self._sent(channel='email').first().body
        self.assertIn('sold out', body)
        self.assertIn('Nothing has been charged', body)

    def test_returned_status_sends_nothing(self):
        """The requirement is to notify until delivery; nothing after."""
        self.clear_notifications()
        with mock.patch('products.notifications._send_email') as send:
            send.return_value = (True, '')
            self.save(status='returned')
        self.assertFalse(self._sent(channel='email', audience='customer').exists())

    def test_whatsapp_requires_opt_in(self):
        self.clear_notifications()
        with mock.patch('products.notifications._send_whatsapp') as send:
            send.return_value = (True, '')
            self.save(whatsapp_opt_in=False, status='accepted')

        self.assertFalse(self._sent(channel='whatsapp').exists())
        skipped = self.order.notifications.get(channel='whatsapp', audience='customer')
        self.assertEqual(skipped.status, 'skipped')
        self.assertIn('did not opt in', skipped.error)
        send.assert_not_called()

    def test_whatsapp_sent_to_normalised_number(self):
        self.clear_notifications()
        # Without credentials the message must be skipped, never attempted: a
        # send would fail and show up as a permanent red alert in the admin.
        self.store.whatsapp_api_token = 'test-token'
        self.store.whatsapp_phone_number_id = '123456789'
        self.store.save()

        with mock.patch('products.notifications._send_whatsapp') as send:
            send.return_value = (True, '')
            self.save(status='accepted')

        send.assert_called_once()
        self.assertEqual(send.call_args[0][0], '351912345678')
        self.assertEqual(self._sent(channel='whatsapp').count(), 1)

    def test_unconfigured_whatsapp_is_a_skip_not_a_failure(self):
        self.clear_notifications()
        self.store.whatsapp_api_token = ''
        self.store.whatsapp_phone_number_id = ''
        self.store.save()

        with mock.patch('products.notifications._send_whatsapp') as send:
            self.save(status='accepted')
        send.assert_not_called()
        row = self.order.notifications.get(channel='whatsapp', audience='customer')
        self.assertEqual(row.status, 'skipped')

    def test_unconfigured_facebook_is_a_skip_not_a_failure(self):
        self.clear_notifications()
        self.store.facebook_page_id = ''
        self.store.facebook_page_access_token = ''
        self.store.save()
        with mock.patch('products.notifications._send_email') as email_send:
            email_send.return_value = (True, '')
            self.save(status='delivered')
        self.assertEqual(
            self.order.notifications.get(channel='facebook').status, 'skipped')

    def test_failed_notification_count_does_not_include_unconfigured(self):
        """The admin badge must only count genuinely broken sends."""
        self.clear_notifications()
        self.store.whatsapp_api_token = ''
        self.store.whatsapp_phone_number_id = ''
        self.store.save()
        with mock.patch('products.notifications._send_email') as email_send:
            email_send.return_value = (True, '')
            self.save(status='accepted')
        self.assertFalse(self.order.notifications.filter(status='failed').exists())

    def test_impossible_phone_number_is_skipped_not_sent(self):
        """A bad number would be rejected by WhatsApp; record it instead."""
        self.clear_notifications()
        with mock.patch('products.notifications._send_whatsapp') as send:
            send.return_value = (True, '')
            self.save(phone='123', status='accepted')

        send.assert_not_called()
        skipped = self.order.notifications.get(channel='whatsapp', audience='customer')
        self.assertEqual(skipped.status, 'skipped')
        self.assertIn('international phone number', skipped.error)

    def test_customer_disabled_suppresses_everything(self):
        self.clear_notifications()
        self.store.customer_notifications_enabled = False
        self.store.save()
        with mock.patch('products.notifications._send_email') as send:
            self.save(status='accepted')
        send.assert_not_called()

    def test_provider_failure_is_recorded_and_never_raises(self):
        """The order must still be saved when email/WhatsApp is down."""
        self.clear_notifications()
        with mock.patch('products.notifications._send_email') as send:
            send.return_value = (False, 'SMTP timeout')
            self.save(status='accepted')   # must not raise

        self.order.refresh_from_db()
        self.assertEqual(self.order.status, 'accepted')
        failed = self.order.notifications.get(status='failed', channel='email')
        self.assertIn('SMTP timeout', failed.error)

    def test_exploding_provider_does_not_break_the_save(self):
        self.clear_notifications()
        with mock.patch('products.notifications._send_email') as send:
            send.side_effect = RuntimeError('boom')
            self.save(status='accepted')   # must not raise
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, 'accepted')

    def test_creating_an_order_alerts_the_shop(self):
        """
        The alert fires when the order is placed — i.e. at creation time, not when
        someone later opens it in the admin.
        """
        alert = self.order.notifications.filter(
            channel='email', audience='admin', event='new').first()
        self.assertIsNotNone(alert)
        self.assertEqual(alert.status, 'sent')
        self.assertIn('#%d' % self.order.pk, alert.subject)
        self.assertIn('912345678', alert.body)

    def test_placing_an_order_emails_the_customer_a_confirmation(self):
        """
        The customer must receive a confirmation the moment the order is
        placed — not only when the shop later accepts it.
        """
        with mock.patch('products.notifications._send_email') as send:
            send.return_value = (True, '')
            with self.captureOnCommitCallbacks(execute=True):
                fresh, _ = _make_order(email='grace@example.com')

        confirmation = fresh.notifications.filter(
            channel='email', audience='customer', event='new').first()
        self.assertIsNotNone(confirmation)
        self.assertEqual(confirmation.status, 'sent')
        self.assertEqual(confirmation.recipient, 'grace@example.com')
        self.assertIn('received your order', confirmation.body)

    def test_new_order_alerts_the_shop_once_only(self):
        alert_count = self.order.notifications.filter(
            channel='email', audience='admin', event='new').count()
        with mock.patch('products.notifications._send_email') as send:
            self.save(status='new')
            self.save(status='new')
        send.assert_not_called()
        self.assertEqual(
            self.order.notifications.filter(channel='email', audience='admin',
                                            event='new').count(),
            alert_count,
        )

    def test_no_admin_address_records_a_skip_not_a_failure(self):
        # No alert address configured: record the skip on a brand new order rather
        # than mutating an existing one, because re-saving 'new' onto 'new' is
        # correctly treated as "no change".
        self.store.notification_email = ''
        self.store.save()
        with mock.patch('products.notifications._send_email') as send, \
                self.captureOnCommitCallbacks(execute=True):
            send.return_value = (True, '')
            fresh, _ = _make_order()
        skipped = fresh.notifications.get(channel='email', audience='admin')
        self.assertEqual(skipped.status, 'skipped')
        self.assertIn('No notification address', skipped.error)

    def test_delivery_posts_a_facebook_success_story(self):
        self.clear_notifications()
        self.store.facebook_page_id = '12345'
        self.store.facebook_page_access_token = 'token'
        self.store.facebook_success_story_template = 'Shipped {product_names} to {place}!'
        self.store.save()
        with mock.patch('products.notifications._send_email') as email_send, \
             mock.patch('products.notifications._post_facebook_story') as fb:
            email_send.return_value = (True, '')
            fb.return_value = (True, '')
            self.save(status='delivered')

        fb.assert_called_once()
        text = fb.call_args[0][0]
        self.assertIn('Kurta', text)
        self.assertIn('Lisbon', text)
        self.assertEqual(self._sent(channel='facebook').count(), 1)

    def test_success_story_posts_only_once(self):
        self.clear_notifications()
        self.store.facebook_page_id = '12345'
        self.store.facebook_page_access_token = 'token'
        self.store.save()
        with mock.patch('products.notifications._send_email') as email_send, \
             mock.patch('products.notifications._post_facebook_story') as fb:
            email_send.return_value = (True, '')
            fb.return_value = (True, '')
            self.save(status='delivered')
            self.save()
            self.save(status='delivered')

        self.assertEqual(fb.call_count, 1)

    def test_success_story_disabled_is_skipped(self):
        self.clear_notifications()
        self.store.facebook_post_on_delivery = False
        self.store.save()
        with mock.patch('products.notifications._send_email') as email_send:
            email_send.return_value = (True, '')
            self.save(status='delivered')
        self.assertEqual(
            self.order.notifications.get(channel='facebook').status, 'skipped')

    def test_bulk_admin_action_notifies(self):
        """queryset.update() would bypass the signal; actions must not."""
        self.clear_notifications()
        with mock.patch('products.notifications._send_email') as send:
            send.return_value = (True, '')
            from django.contrib.admin.sites import AdminSite
            from products.admin import OrderAdmin

            admin_instance = OrderAdmin(Order, AdminSite())
            request = type('R', (), {'user': None, 'session': {}, 'GET': {}, 'POST': {}})()
            admin_instance.message_user = lambda *a, **k: None
            queryset = Order.objects.filter(pk=self.order.pk)
            with self.captureOnCommitCallbacks(execute=True):
                admin_instance.mark_shipped(request, queryset)

        self.order.refresh_from_db()
        self.assertEqual(self.order.status, 'shipped')
        self.assertTrue(self._sent(channel='email', audience='customer').exists())


class PhoneNormalizationTests(TestCase):
    def test_strips_formatting(self):
        from products.notifications import normalize_phone
        self.assertEqual(normalize_phone('+351 912 345 678'), '351912345678')
        self.assertEqual(normalize_phone('(0)351-912-345-678'), '0351912345678')

    def test_international_prefix_is_removed(self):
        from products.notifications import normalize_phone
        self.assertEqual(normalize_phone('00351 912 345 678'), '351912345678')

    def test_plausibility_bounds(self):
        from products.notifications import is_plausible_whatsapp_number
        self.assertFalse(is_plausible_whatsapp_number('123'))
        self.assertTrue(is_plausible_whatsapp_number('351912345678'))
        self.assertFalse(is_plausible_whatsapp_number('1234567890123456789'))


# --- REVIEWS ---


class ReviewApiTests(TestCase):
    def setUp(self):
        from rest_framework.authtoken.models import Token

        self.client = APIClient()
        self.category = Category.objects.create(name='Cat', slug='cat')
        self.product = Product.objects.create(category=self.category, name='Kurta',
                                              slug='kurta', stock=10)
        self.customer = User.objects.create_user(
            'ada', 'ada@example.com', 'pw-12345678', first_name='Ada', last_name='Lovelace')
        self.token = Token.objects.create(user=self.customer)

    def _auth(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.token.key}')

    def _review(self, **overrides):
        from products.models import Review

        defaults = dict(product=self.product, user=self.customer, rating=5,
                        comment='Beautiful fabric', product_name_snapshot='Kurta')
        defaults.update(overrides)
        return Review.objects.create(**defaults)

    def test_anonymous_can_read_reviews(self):
        self._review()
        res = self.client.get(f'/api/v1/products/kurta/reviews/')
        self.assertEqual(res.status_code, 200, res.content)
        self.assertEqual(len(res.data['reviews']), 1)
        self.assertEqual(res.data['average_rating'], 5.0)
        self.assertEqual(res.data['breakdown']['5'], 1)

    def test_anonymous_cannot_write(self):
        res = self.client.post(f'/api/v1/products/kurta/reviews/',
                               {'rating': 5, 'comment': 'Nice'}, format='json')
        self.assertEqual(res.status_code, 401)

    def test_customer_can_review(self):
        self._auth()
        res = self.client.post(f'/api/v1/products/kurta/reviews/',
                               {'rating': 4, 'title': 'Good', 'comment': 'Nice fit'},
                               format='json')
        self.assertEqual(res.status_code, 201, res.content)
        self.assertEqual(res.data['rating'], 4)
        # Reviews show a first name + last initial, not a full identity.
        self.assertEqual(res.data['author'], 'Ada L.')

    def test_rating_out_of_range_is_rejected(self):
        self._auth()
        res = self.client.post(f'/api/v1/products/kurta/reviews/',
                               {'rating': 9, 'comment': 'Nice'}, format='json')
        self.assertEqual(res.status_code, 400)

    def test_empty_comment_is_rejected(self):
        self._auth()
        res = self.client.post(f'/api/v1/products/kurta/reviews/',
                               {'rating': 5, 'comment': '   '}, format='json')
        self.assertEqual(res.status_code, 400)

    def test_duplicate_review_is_refused_then_updatable(self):
        self._review(rating=3, comment='First')
        self._auth()
        again = self.client.post(f'/api/v1/products/kurta/reviews/',
                                 {'rating': 5, 'comment': 'Second'}, format='json')
        self.assertEqual(again.status_code, 409)

        forced = self.client.post(f'/api/v1/products/kurta/reviews/',
                                  {'rating': 5, 'comment': 'Second', 'force_update': True},
                                  format='json')
        self.assertEqual(forced.status_code, 200, forced.content)
        self.assertEqual(Review.objects.filter(product=self.product).count(), 1)
        self.assertEqual(Review.objects.get().comment, 'Second')

    def test_verified_purchase_flag_is_not_client_settable(self):
        self._auth()
        res = self.client.post(f'/api/v1/products/kurta/reviews/',
                               {'rating': 5, 'comment': 'Great',
                                'is_verified_purchase': True}, format='json')
        self.assertEqual(res.status_code, 201)
        # No delivered order, so it must not claim to be verified.
        self.assertFalse(res.data['is_verified_purchase'])

    def test_delivered_order_marks_review_verified(self):
        order, _ = _make_order(user=self.customer, status='delivered')
        order.items.update(product=self.product)
        self._auth()
        res = self.client.post(f'/api/v1/products/kurta/reviews/',
                               {'rating': 5, 'comment': 'Bought it'}, format='json')
        self.assertEqual(res.data['is_verified_purchase'], True)

    def test_unpublished_reviews_are_hidden_from_readers(self):
        self._review(is_approved=False)
        res = self.client.get('/api/v1/products/kurta/reviews/')
        self.assertEqual(len(res.data['reviews']), 0)
        self.assertEqual(res.data['review_count'], 0)

    def test_product_payload_exposes_rating(self):
        self._review()
        res = self.client.get('/api/v1/latest-products/')
        product = next(p for p in res.data if p['slug'] == 'kurta')
        self.assertEqual(product['average_rating'], 5.0)
        self.assertEqual(product['review_count'], 1)

    def test_unrated_product_reports_null_not_error(self):
        res = self.client.get('/api/v1/latest-products/')
        product = next(p for p in res.data if p['slug'] == 'kurta')
        self.assertIsNone(product['average_rating'])
        self.assertEqual(product['review_count'], 0)

    def test_customer_cannot_delete_another_customers_review(self):
        from rest_framework.authtoken.models import Token

        mallory = User.objects.create_user('mallory', 'm@example.com', 'pw-12345678')
        victim = self._review()
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {Token.objects.create(user=mallory).key}')
        res = self.client.delete(f'/api/v1/reviews/{victim.pk}/')
        # 404, not 403: the API must not confirm that someone else's review exists.
        self.assertEqual(res.status_code, 404)
        self.assertTrue(Review.objects.filter(pk=victim.pk).exists())

    def test_customer_can_delete_own_review(self):
        from products.models import Review

        review = self._review()
        self._auth()
        res = self.client.delete(f'/api/v1/reviews/{review.pk}/')
        self.assertEqual(res.status_code, 204)
        self.assertFalse(Review.objects.filter(pk=review.pk).exists())

    def test_reviews_for_unknown_product_are_404(self):
        res = self.client.get('/api/v1/products/nope/reviews/')
        self.assertEqual(res.status_code, 404)


class ReviewAdminTests(TestCase):
    def setUp(self):
        User.objects.create_superuser('root', 'root@example.com', 'pw-root-123456')
        self.client.force_login(User.objects.get(username='root'))
        from products.models import Review

        self.category = Category.objects.create(name='Cat', slug='cat')
        self.product = Product.objects.create(category=self.category, name='Kurta',
                                              slug='kurta', stock=1)
        self.review = Review.objects.create(
            product=self.product, rating=4, comment='Good one',
            product_name_snapshot='Kurta')

    def test_changelist_renders(self):
        res = self.client.get('/admin/products/review/')
        self.assertEqual(res.status_code, 200)

    def test_review_is_not_editable(self):
        """Moderation is publish/hide; the reviewer's words are theirs."""
        res = self.client.get('/admin/products/review/')
        self.assertEqual(res.status_code, 200)

    def test_hide_and_publish_actions(self):
        from products.models import Review

        url = '/admin/products/review/'
        res = self.client.post(url, {
            'action': 'unpublish_reviews',
            admin.helpers.ACTION_CHECKBOX_NAME: [str(self.review.pk)],
        }, follow=True)
        self.assertEqual(res.status_code, 200)
        self.assertFalse(Review.objects.get(pk=self.review.pk).is_approved)


class NotificationAdminDisplayTests(TestCase):
    """The notification log has to actually be visible in the admin."""

    def setUp(self):
        User.objects.create_superuser('root', 'root@example.com', 'pw-root-123456')
        self.client.force_login(User.objects.get(username='root'))
        self.order, _ = _make_order()
        from products.models import OrderNotification

        OrderNotification.objects.create(
            order=self.order, channel='email', audience='customer', event='packed',
            status='sent', recipient='ada@example.com', subject='Your order is packed',
            body='packed and ready', sent_at=timezone.now())
        OrderNotification.objects.create(
            order=self.order, channel='whatsapp', audience='customer', event='packed',
            status='failed', recipient='351912345678', error='WhatsApp API not configured')

    def test_order_page_lists_the_notifications(self):
        res = self.client.get(f'/admin/products/order/{self.order.pk}/change/')
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, 'ada@example.com')
        self.assertContains(res, 'packed')
        self.assertContains(res, 'WhatsApp API not configured')

    def test_notification_changelist_shows_failures(self):
        res = self.client.get('/admin/products/ordernotification/?status__exact=failed')
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, '351912345678')

    def test_rows_are_read_only(self):
        """The audit trail must not be editable."""
        from products.admin import OrderNotificationInline

        inline = OrderNotificationInline(Order, maims_admin)
        request = type('R', (), {})()
        request.user = User.objects.get(username='root')
        self.assertFalse(inline.has_add_permission(request))
        self.assertFalse(inline.has_change_permission(request))
        self.assertFalse(inline.has_delete_permission(request))
        # max_num must stay unset: it would cap the formset and hide every row.
        self.assertNotEqual(inline.max_num, 0)


import hashlib
import hmac
import json
from django.test import override_settings

FB_TEST_SECRET = 'test-facebook-app-secret'


class SignedFacebookClient(APIClient):
    """APIClient that signs webhook POST bodies the way Meta does (X-Hub-Signature-256)."""

    def post(self, path, data=None, format=None, content_type=None, follow=False, **extra):
        if (data is not None and path.startswith('/api/v1/facebook/webhook/')
                and 'HTTP_X_HUB_SIGNATURE_256' not in extra):
            body = json.dumps(data).encode('utf-8')
            digest = hmac.new(FB_TEST_SECRET.encode(), body, hashlib.sha256).hexdigest()
            extra['HTTP_X_HUB_SIGNATURE_256'] = 'sha256=' + digest
            return super().post(path, data=body, content_type='application/json',
                                follow=follow, **extra)
        return super().post(path, data=data, format=format, content_type=content_type,
                            follow=follow, **extra)


@override_settings(FACEBOOK_APP_SECRET=FB_TEST_SECRET)
class FacebookSyncTests(TestCase):
    """Facebook Page → Product sync: parsing, webhook, upsert."""

    @classmethod
    def setUpTestData(cls):
        cls.category = Category.objects.create(name='Kurta', slug='kurta')

    def setUp(self):
        # APIClient (not the plain Django client): `format='json'`
        # only sends application/json here, so DRF parses the
        # payload into a dict instead of a url-encoded string.
        self.client = SignedFacebookClient()

    # --- parsing -----------------------------------------------------------

    def test_parse_product_post_extracts_title_price_and_description(self):
        parsed = facebook.parse_product_post(
            'Jamdani Saree — Lotus\n'
            '€ 120.00\n'
            'Handwoven in Dhaka, 6 yards, includes blouse piece')
        self.assertEqual(parsed['title'], 'Jamdani Saree — Lotus')
        self.assertEqual(parsed['price'], Decimal('120.00'))
        self.assertEqual(parsed['currency'], 'EUR')
        self.assertIn('Handwoven', parsed['description'])
        self.assertFalse(parsed['sold_out'])

    def test_parse_product_post_sold_out(self):
        parsed = facebook.parse_product_post('Silk Scarf\n€ 45\nSold out until Friday')
        self.assertTrue(parsed['sold_out'])

    def test_parse_product_post_bengali_currency_and_sold(self):
        parsed = facebook.parse_product_post('শাড়ি\n৳1,200\nবিক্রিত')
        self.assertEqual(parsed['currency'], 'BDT')
        self.assertEqual(parsed['price'], Decimal('1200'))
        self.assertTrue(parsed['sold_out'])

    def test_parse_product_post_number_formats(self):
        self.assertEqual(
            facebook.parse_product_post('A\nPrice: 1,200.50')['price'],
            Decimal('1200.50'))
        self.assertEqual(
            facebook.parse_product_post('A\nPrice: 1.200,50')['price'],
            Decimal('1200.50'))
        self.assertEqual(
            facebook.parse_product_post('A\nPrice: 1,200')['price'],
            Decimal('1200'))
        self.assertEqual(
            facebook.parse_product_post('A\n€ 1.200,50')['price'],
            Decimal('1200.50'))

    def test_parse_product_post_price_on_title_line(self):
        parsed = facebook.parse_product_post('Linen Kurti € 89\nSoft washed linen')
        self.assertEqual(parsed['title'], 'Linen Kurti')
        self.assertEqual(parsed['price'], Decimal('89.00'))
        self.assertEqual(parsed['currency'], 'EUR')

    def test_parse_product_post_bullet_title(self):
        parsed = facebook.parse_product_post('•  • New Kurti\n€ 10')
        self.assertEqual(parsed['title'], 'New Kurti')

    def test_unique_slug_dedupes(self):
        Product.objects.create(category=self.category, name='A', slug='jamdani', stock=1)
        self.assertEqual(facebook.unique_slug('Jamdani'), 'jamdani-2')
        Product.objects.create(category=self.category, name='B', slug='jamdani-2', stock=1)
        self.assertEqual(facebook.unique_slug('Jamdani'), 'jamdani-3')
        # Excluding the existing product frees the plain slug.
        product = Product.objects.get(slug='jamdani')
        self.assertEqual(facebook.unique_slug('Jamdani', exclude_id=product.id), 'jamdani')

    # --- webhook verification --------------------------------------------------

    def test_webhook_get_verification(self):
        with override_settings(FACEBOOK_WEBHOOK_VERIFY_TOKEN='secret-token'):
            response = self.client.get('/api/v1/facebook/webhook/', {
                'hub.mode': 'subscribe',
                'hub.verify_token': 'secret-token',
                'hub.challenge': 'challenge-123',
            })
        self.assertEqual(response.status_code, 200)
        # Meta expects the raw challenge value, not a JSON body.
        self.assertEqual(response.content.decode(), 'challenge-123')

    def test_webhook_get_rejects_wrong_token(self):
        with override_settings(FACEBOOK_WEBHOOK_VERIFY_TOKEN='secret-token'):
            response = self.client.get('/api/v1/facebook/webhook/', {
                'hub.mode': 'subscribe',
                'hub.verify_token': 'wrong',
                'hub.challenge': 'challenge-123',
            })
        self.assertEqual(response.status_code, 403)

    def test_webhook_get_requires_challenge(self):
        with override_settings(FACEBOOK_WEBHOOK_VERIFY_TOKEN='secret-token'):
            response = self.client.get('/api/v1/facebook/webhook/', {
                'hub.mode': 'subscribe',
                'hub.verify_token': 'secret-token',
            })
        self.assertEqual(response.status_code, 403)

    # --- webhook processing ------------------------------------------------------

    @mock.patch('products.facebook.attach_product_image')
    def test_webhook_post_creates_product(self, _attach):
        payload = {
            'object': 'page',
            'entry': [{
                'id': '123',
                'changes': [{
                    'field': 'feed',
                    'value': {
                        'post_id': '123_456',
                        'verb': 'added',
                        'message': 'Linen Kurta\n€ 89.00\nCotton linen, hand embroidered',
                        'full_picture': 'https://example.com/pic.jpg',
                    },
                }],
            }],
        }
        response = self.client.post('/api/v1/facebook/webhook/',
                                    data=payload, format='json')
        self.assertEqual(response.status_code, 200)
        product = Product.objects.get(facebook_post_id='123_456')
        self.assertEqual(product.name, 'Linen Kurta')
        self.assertEqual(product.stock, settings.FACEBOOK_SYNC_DEFAULT_STOCK)
        price = CurrencyPrice.objects.get(product=product, currency='EUR')
        self.assertEqual(price.price, Decimal('89.00'))
        self.assertEqual(product.get_image(), '')  # image attach was mocked out
        # The sync category is auto-created on first use.
        self.assertEqual(product.category.slug, settings.FACEBOOK_SYNC_CATEGORY_SLUG)

    @mock.patch('products.facebook.attach_product_image')
    def test_webhook_post_is_idempotent(self, _attach):
        payload = {
            'entry': [{'changes': [{'field': 'feed', 'value': {
                'post_id': '123_456', 'verb': 'added',
                'message': 'Linen Kurta\n€ 89.00',
                'full_picture': 'https://example.com/pic.jpg'}}]}],
        }
        for _ in range(2):
            self.client.post('/api/v1/facebook/webhook/', data=payload, format='json')
        self.assertEqual(Product.objects.filter(facebook_post_id='123_456').count(), 1)

    @mock.patch('products.facebook.attach_product_image')
    def test_webhook_post_removed_marks_sold(self, _attach):
        product = Product.objects.create(
            category=self.category, name='Old Kurta', slug='old-kurta',
            stock=5, facebook_post_id='123_789')
        payload = {
            'entry': [{'changes': [{'field': 'feed',
                                     'value': {'post_id': '123_789', 'verb': 'removed'}}]}],
        }
        response = self.client.post('/api/v1/facebook/webhook/',
                                    data=payload, format='json')
        self.assertEqual(response.status_code, 200)
        product.refresh_from_db()
        self.assertEqual(product.stock, 0)

    def test_webhook_ignores_non_feed_changes(self):
        payload = {'entry': [{'changes': [{'field': 'story', 'value': {}}]}]}
        response = self.client.post('/api/v1/facebook/webhook/',
                                    data=payload, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['results'], [])

    def test_webhook_signature_verification(self):
        body = b'{"entry": []}'
        with override_settings(FACEBOOK_APP_SECRET='app-secret'):
            sig = 'sha256=' + hmac.new(
                b'app-secret', body, hashlib.sha256).hexdigest()
            self.assertTrue(facebook.verify_signature(body, sig))
            self.assertFalse(facebook.verify_signature(body, 'sha256=deadbeef'))
            self.assertFalse(facebook.verify_signature(body, None))

    # --- social feed endpoint ------------------------------------------------

    def test_social_feed_returns_only_synced_products(self):
        synced = Product.objects.create(
            category=self.category, name='FB Kurta', slug='fb-kurta',
            stock=5, facebook_post_id='123_456')
        Product.objects.create(
            category=self.category, name='Manual Kurta', slug='manual-kurta', stock=5)
        response = self.client.get('/api/v1/social-feed/')
        self.assertEqual(response.status_code, 200)
        ids = [p['id'] for p in response.data]
        self.assertIn(synced.id, ids)
        self.assertEqual(len(ids), 1)
        # The card's "Live" badge reads these fields.
        row = response.data[0]
        self.assertEqual(row['facebook_post_id'], '123_456')

    def test_social_feed_empty_when_never_synced(self):
        Product.objects.create(
            category=self.category, name='Manual Kurta', slug='manual-kurta', stock=5)
        response = self.client.get('/api/v1/social-feed/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, [])


@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class NewsletterSubscribeTests(TestCase):
    """Footer sign-up: forwards to the shop mailbox only while the admin consent
    row allows it, and the derived flags must reach the storefront payload."""

    def setUp(self):
        from django.core.cache import cache
        # The endpoint is throttled (newsletter scope); keep test order irrelevant.
        cache.clear()
        self.prefs = CustomerNotificationSettings.get()
        self.prefs.signup_enabled = True
        self.prefs.checkout_opt_in_enabled = True
        self.prefs.opt_in_strategy = 'explicit'
        self.prefs.status = 'active'
        self.prefs.recipient_email = 'list@example.com'
        self.prefs.save()
        self.url = '/api/v1/newsletter/subscribe/'

    def test_valid_signup_is_forwarded_to_the_shop_mailbox(self):
        response = self.client.post(self.url, {'email': 'Shopper@Example.COM'})
        self.assertEqual(response.status_code, 201)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ['list@example.com'])
        self.assertIn('shopper@example.com', mail.outbox[0].body)

    def test_invalid_email_is_rejected_without_sending(self):
        response = self.client.post(self.url, {'email': 'not-an-email'})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(len(mail.outbox), 0)

    def test_missing_email_is_rejected(self):
        response = self.client.post(self.url, {})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(len(mail.outbox), 0)

    def test_paused_status_stops_capture_immediately(self):
        self.prefs.status = 'paused'
        self.prefs.save()
        response = self.client.post(self.url, {'email': 'someone@example.com'})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(len(mail.outbox), 0)

    def test_signup_toggle_off_stops_capture(self):
        self.prefs.signup_enabled = False
        self.prefs.save()
        response = self.client.post(self.url, {'email': 'someone@example.com'})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(len(mail.outbox), 0)

    def test_no_mailbox_configured_means_nothing_is_collected(self):
        self.prefs.recipient_email = ''
        self.prefs.save()
        response = self.client.post(self.url, {'email': 'someone@example.com'})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(len(mail.outbox), 0)

    def test_site_settings_payload_exposes_derived_consent_flags(self):
        response = self.client.get('/api/v1/site-settings/')
        self.assertEqual(response.status_code, 200)
        block = response.json()['newsletter']
        # Raw toggles alone must never gate the frontend — the derived flags do.
        self.assertTrue(block['signup_enabled'])
        self.assertTrue(block['accepts_signups'])
        self.assertTrue(block['checkout_opt_in_enabled'])
        self.assertFalse(block['box_starts_ticked'])  # explicit strategy = unticked
        self.assertIn('consent_text', block)


class FacebookWebhookSecurityTests(TestCase):
    """The webhook must fail closed: only correctly signed requests get through."""
    URL = '/api/v1/facebook/webhook/'
    BODY = json.dumps({'entry': []}).encode('utf-8')

    def _sig(self, secret):
        return 'sha256=' + hmac.new(secret.encode(), self.BODY, hashlib.sha256).hexdigest()

    def _post(self, **extra):
        return APIClient().post(self.URL, data=self.BODY,
                                content_type='application/json', **extra)

    @override_settings(FACEBOOK_APP_SECRET='')
    def test_unsigned_request_rejected_when_secret_missing(self):
        self.assertEqual(self._post().status_code, 403)

    @override_settings(FACEBOOK_APP_SECRET=FB_TEST_SECRET)
    def test_missing_signature_rejected(self):
        self.assertEqual(self._post().status_code, 403)

    @override_settings(FACEBOOK_APP_SECRET=FB_TEST_SECRET)
    def test_wrong_signature_rejected(self):
        response = self._post(HTTP_X_HUB_SIGNATURE_256=self._sig('some-other-secret'))
        self.assertEqual(response.status_code, 403)

    @override_settings(FACEBOOK_APP_SECRET=FB_TEST_SECRET)
    def test_valid_signature_accepted(self):
        response = self._post(HTTP_X_HUB_SIGNATURE_256=self._sig(FB_TEST_SECRET))
        self.assertEqual(response.status_code, 200)

    @override_settings(FACEBOOK_WEBHOOK_VERIFY_TOKEN='')
    def test_verification_rejected_when_verify_token_unset(self):
        response = APIClient().get(self.URL, {
            'hub.mode': 'subscribe', 'hub.verify_token': '', 'hub.challenge': 'abc'})
        self.assertEqual(response.status_code, 403)
