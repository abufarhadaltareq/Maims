import threading
from decimal import Decimal
from types import SimpleNamespace
from unittest import mock, skipIf

from django.contrib.auth.models import User
from django.db import connection
from django.test import TestCase, TransactionTestCase
from rest_framework.test import APIClient

from .models import Category, CurrencyPrice, Order, Product, UserProfile
from .views import _build_order_items, _CheckoutError, _mark_paid_and_reserve, _reserve_stock


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
            'place': 'Lisbon', 'payment_method': 'cod', 'currency': 'EUR',
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
        # 2 x 10.00 from the DB, NOT the forged 0.01.
        self.assertEqual(order.total_amount, Decimal('20.00'))

    def test_missing_required_fields_rejected(self):
        res = self.client.post('/api/v1/checkout/',
                               self._payload(email=''), format='json')
        self.assertEqual(res.status_code, 400)
        self.assertFalse(Order.objects.exists())

    def test_empty_cart_rejected(self):
        res = self.client.post('/api/v1/checkout/',
                               self._payload(items=[]), format='json')
        self.assertEqual(res.status_code, 400)


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
            'phone': '', 'address': '1 Main St', 'zipcode': '1000', 'place': 'Lisbon',
            'payment_method': 'cod', 'currency': currency,
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
        self.assertEqual(Order.objects.get().total_amount, Decimal('100.00'))


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
            'phone': '', 'address': '1 Main St', 'zipcode': '1000', 'place': 'Lisbon',
            'payment_method': 'cod', 'currency': 'EUR',
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
        self.assertEqual(order.total_amount, Decimal('20.00'))
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
            currency='EUR', payment_method='cod', is_paid=False,
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
                    'phone': '', 'address': 'x', 'zipcode': '1', 'place': 'y',
                    'payment_method': 'cod', 'currency': 'EUR',
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


