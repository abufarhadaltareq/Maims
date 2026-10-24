import logging

import binascii
import stripe
import os
from decimal import Decimal, ROUND_HALF_UP
from django.conf import settings
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.tokens import default_token_generator
from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from django.http import Http404, HttpResponse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from rest_framework.views import APIView
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.throttling import SimpleRateThrottle
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth.models import User
from django.db import transaction
from django.db.models import Avg, Count, F, Prefetch, Q
from rest_framework.authtoken.models import Token
from .models import Category, CurrencyPrice, CustomerNotificationSettings, HeroBannerSettings, HeroSlide, Order, OrderItem, Product, Review, SiteSettings, UserProfile, WishlistItem
from . import facebook
from . import notifications
from .serializers import (
    CategorySerializer, CustomerNotificationSettingsSerializer, HeroBannerSettingsSerializer, HeroSlideSerializer, OrderSerializer,
    ProductSerializer, ReviewCreateSerializer,
    ReviewSerializer, SiteSettingsSerializer, UserProfileSerializer,
    RegisterSerializer, UserSerializer, WishlistAddSerializer, WishlistItemSerializer,
)
from .chatbot import ChatbotAgent

logger = logging.getLogger(__name__)
DELIVERY_FEE_SEK = Decimal('85.00')
RATES_TO_USD = {
    'SEK': Decimal('0.095'),
    'PKR': Decimal('0.0036'),
    'EUR': Decimal('1.08'),
    'BDT': Decimal('0.0085'),
    'USD': Decimal('1.0'),
}

# 🔑 Make sure STRIPE_SECRET_KEY is added to your settings.py
stripe.api_key = settings.STRIPE_SECRET_KEY

STRIPE_PUBLISHABLE_KEY = settings.STRIPE_PUBLISHABLE_KEY


# --- Rate limiting for abuse-prone endpoints ---
class _ScopedThrottle(SimpleRateThrottle):
    """Throttle per-user when authenticated, otherwise per client IP."""

    def get_cache_key(self, request, view):
        if request.user and request.user.is_authenticated:
            ident = request.user.pk
        else:
            ident = self.get_ident(request)
        return self.cache_format % {'scope': self.scope, 'ident': ident}


class AuthThrottle(_ScopedThrottle):
    """Slows credential-stuffing / registration / password-change abuse."""
    scope = 'auth'


class CheckoutThrottle(_ScopedThrottle):
    """Slows order-spam and Stripe PaymentIntent abuse."""
    scope = 'checkout'


class NewsletterThrottle(_ScopedThrottle):
    """Caps address-harvesting / mail-bombing via the footer sign-up form."""
    scope = 'newsletter'


class ChatbotThrottle(_ScopedThrottle):
    """Caps AI chatbot requests to prevent scraping and abuse."""
    scope = 'chatbot'


# --- 🌟 RESTORED: PRODUCT VIEWS ---

def product_queryset():
    """
    The one queryset every catalogue endpoint uses.

    Every relationship ProductSerializer touches is joined or prefetched here:
    prices (for the displayed price), media (the gallery) and category (nested,
    along with its children and its product count). The nested category serializer
    otherwise runs a COUNT per product, which turned a 20-item listing into 24
    queries and a 200-item listing into 200+.

    `category` is prefetched rather than select_related: it cannot be both, and
    doing both makes Django issue a redundant join plus the prefetch query.
    """
    # `rating_average`/`rating_count` are filtered in SQL so the star rating on the
    # product card costs nothing; Product.average_rating would otherwise run a
    # query per product.
    return Product.objects.annotate(
        rating_average=Avg('reviews__rating', filter=Q(reviews__is_approved=True)),
        rating_count=Count('reviews', filter=Q(reviews__is_approved=True), distinct=True),
    ).prefetch_related(
        'prices',
        'media',
        Prefetch(
            'category',
            queryset=Category.objects.annotate(
                product_count=Count(
                    'products',
                    filter=Q(products__is_visible=True),
                )
            ).prefetch_related('children'),
        ),
    )


def apply_catalog_filters(queryset, params):
    """Shared ?size= ?color= ?fabric= ?length= filtering for catalogue views.

    Matches deshi-besh style browsing: comma-separated multi-values, case
    insensitive. Size/length/color live in comma-separated CharFields so we
    match with icontains per value; fabric is an exact choice field.
    """
    def _values(key):
        raw = params.get(key) or params.get(f'{key}s') or ''
        return [v.strip() for v in str(raw).split(',') if v.strip()]

    for size in _values('size'):
        queryset = queryset.filter(size_options__icontains=size)
    for color in _values('color'):
        queryset = queryset.filter(color_options__icontains=color)
    for length in _values('length'):
        queryset = queryset.filter(length_options__icontains=length)
    fabrics = _values('fabric')
    if fabrics:
        q = Q()
        for fabric in fabrics:
            q |= Q(fabric_type__iexact=fabric)
        queryset = queryset.filter(q)
    return queryset


def collect_facets(queryset, limit=60):
    """Distinct sizes, colors, lengths and fabrics present in a queryset."""
    from collections import Counter
    sizes, colors, lengths = Counter(), Counter(), Counter()
    fabrics = Counter()
    for row in queryset.values_list('size_options', 'color_options', 'length_options', 'fabric_type'):
        for counter, raw in ((sizes, row[0]), (colors, row[1]), (lengths, row[2])):
            if raw:
                for part in str(raw).split(','):
                    val = part.strip()
                    if val:
                        counter[val] += 1
        if row[3]:
            fabrics[row[3]] += 1

    def _sorted(counter):
        def _key(item):
            name, _ = item
            try:
                return (0, float(name))
            except ValueError:
                return (1, name.lower())
        return [{'value': name, 'count': count} for name, count in sorted(counter.items(), key=_key)][:limit]

    return {
        'sizes': _sorted(sizes),
        'colors': _sorted(colors),
        'lengths': _sorted(lengths),
        'fabrics': [{'value': name, 'count': count} for name, count in sorted(fabrics.items())],
    }


class LatestProductsList(APIView):
    permission_classes = [AllowAny]

    def get(self, request, format=None):
        category_slug = request.query_params.get('category', '').strip()

        if category_slug and category_slug != 'undefined':
            try:
                category = Category.objects.get(slug=category_slug)
                # Include child categories so parent links show nested products
                child_ids = list(category.children.values_list('id', flat=True))
                products = product_queryset().filter(
                    Q(category=category) | Q(category_id__in=child_ids)
                )
            except Category.DoesNotExist:
                return Response([])
        else:
            products = product_queryset().all()

        # Visible storefront rows only + ?size/?color/?fabric/?length= filters
        # from the deshi-besh style sidebar.
        products = apply_catalog_filters(
            products.filter(is_visible=True), request.query_params)

        serializer = ProductSerializer(products, many=True, context={'request': request})
        return Response(serializer.data)


class ProductFacets(APIView):
    """Distinct sizes/colors/lengths/fabrics for the filter sidebar.

    GET /api/v1/facets/?category=<slug> — scoped to a category when given,
    whole visible catalogue otherwise.
    """
    permission_classes = [AllowAny]

    def get(self, request, format=None):
        qs = product_queryset().filter(is_visible=True)
        category_slug = request.query_params.get('category', '').strip()
        if category_slug and category_slug != 'undefined':
            try:
                category = Category.objects.get(slug=category_slug)
                child_ids = list(category.children.values_list('id', flat=True))
                qs = qs.filter(Q(category=category) | Q(category_id__in=child_ids))
            except Category.DoesNotExist:
                return Response({'sizes': [], 'colors': [], 'lengths': [], 'fabrics': []})
        return Response(collect_facets(qs))


class FavoriteBrandsList(APIView):
    """Brand rail for the catalogue page (deshi-besh 'Favorite Brands').

    Derived from Product.brand_name so the shop never configures it twice:
    the most-used brand names with a representative image each.
    """
    permission_classes = [AllowAny]

    def get(self, request, format=None):
        from django.db.models import Count
        limit = request.query_params.get('limit', '12')
        try:
            limit = max(1, min(int(limit), 30))
        except (TypeError, ValueError):
            limit = 12
        rows = (product_queryset().filter(is_visible=True)
                .exclude(brand_name__isnull=True).exclude(brand_name='')
                .values('brand_name').annotate(total=Count('id'))
                .order_by('-total')[:limit])
        brands = []
        for row in rows:
            name = row['brand_name']
            sample = (product_queryset().filter(is_visible=True, brand_name=name)
                      .order_by('-date_added').first())
            brands.append({
                'name': name,
                'count': row['total'],
                'image': sample.get_image() if sample else '',
                'slug': sample.slug if sample else '',
            })
        return Response(brands)


class SocialFeedList(APIView):
    """Social Live Feed: products synced from the Facebook Page.

    GET /api/v1/social-feed/?limit=12 — newest Facebook-synced products
    first. Empty list (not 404) when the Page has never synced, so the
    homepage shelf renders its graceful empty state.
    """
    permission_classes = [AllowAny]

    def get(self, request, format=None):
        try:
            limit = int(request.query_params.get('limit', '12'))
        except (TypeError, ValueError):
            limit = 12
        limit = max(1, min(limit, 50))
        products = (product_queryset()
                    .filter(facebook_post_id__isnull=False)
                    .filter(is_visible=True)
                    .exclude(facebook_post_id='')
                    .order_by('-date_added')[:limit])
        serializer = ProductSerializer(products, many=True, context={'request': request})
        return Response(serializer.data)

class ProductDetail(APIView):
    """
    Handles fetching data for an individual product's detail page.
    """
    permission_classes = [AllowAny]

    def get(self, request, slug, format=None):
        try:
            product = product_queryset().get(slug=slug, is_visible=True)
            serializer = ProductSerializer(product, context={'request': request})
            return Response(serializer.data)
        except Product.DoesNotExist:
            raise Http404


class CategoryList(APIView):
    """
    Lists all available product categories for navigation.
    Returns top-level parents with nested children + product counts.
    ?homepage=true -> only categories flagged show_on_homepage (for the Shop-by-Category strip).
    """
    permission_classes = [AllowAny]

    def get(self, request, format=None):
        qs = Category.objects.filter(parent__isnull=True).prefetch_related(
            'children', 'children__children'
        ).annotate(
            product_count=Count(
                'products',
                filter=Q(products__is_visible=True),
                distinct=True,
            )
        )
        if request.query_params.get('homepage') == 'true':
            qs = qs.filter(show_on_homepage=True)
        serializer = CategorySerializer(qs, many=True)
        return Response(serializer.data)


class HeroSlideList(APIView):
    """Active hero banner slides for the homepage, ordered by `order`."""
    permission_classes = [AllowAny]

    def get(self, request, format=None):
        slides = HeroSlide.objects.filter(is_active=True).order_by('order', 'id')
        serializer = HeroSlideSerializer(slides, many=True)
        return Response(serializer.data)


class CategoryShowcase(APIView):
    """
    Homepage "Shop by Category" payload: homepage-enabled subcategories only,
    each with up to 8 preview products (nested child products included).
    """
    permission_classes = [AllowAny]

    def get(self, request, format=None):
        cats = Category.objects.filter(
            parent__isnull=False,
            show_on_homepage=True,
        ).annotate(
            product_count=Count(
                'products',
                filter=Q(products__is_visible=True),
                distinct=True,
            )
        ).prefetch_related('children').order_by('homepage_order', 'name')
        payload = []
        for cat in cats:
            child_ids = list(cat.children.values_list('id', flat=True))
            products = product_queryset().filter(
                Q(category=cat) | Q(category_id__in=child_ids),
                is_visible=True,
            )[:8]
            payload.append({
                'category': CategorySerializer(cat).data,
                'products': ProductSerializer(products, many=True, context={'request': request}).data,
            })
        return Response(payload)


class ProductSearch(APIView):
    """Full-text style search across name/brand/description/slugs."""
    permission_classes = [AllowAny]

    def get(self, request, format=None):
        query = request.query_params.get('q', '').strip()
        if not query:
            return Response([])
        products = product_queryset().filter(
            is_visible=True,
        ).filter(
            Q(name__icontains=query)
            | Q(brand_name__icontains=query)
            | Q(description__icontains=query)
            | Q(slug__icontains=query)
            | Q(category__name__icontains=query)
            | Q(category__slug__icontains=query)
        ).distinct()[:50]
        serializer = ProductSerializer(products, many=True, context={'request': request})
        return Response(serializer.data)


class CategoryProducts(APIView):
    """
    Returns products for a selected category.
    """
    permission_classes = [AllowAny]

    def get(self, request, category_slug, format=None):
        try:
            category = Category.objects.get(slug=category_slug)
        except Category.DoesNotExist:
            raise Http404

        child_ids = list(category.children.values_list('id', flat=True))
        products = product_queryset().filter(
            Q(category=category) | Q(category_id__in=child_ids),
            is_visible=True,
        )
        serializer = ProductSerializer(products, many=True, context={'request': request})
        return Response(serializer.data)


# --- 💳 CHECKOUT & ORDER VIEWS ---

class _CheckoutError(Exception):
    """Any client-correctable checkout problem; maps to an HTTP 400 response."""

    def __init__(self, message, status_code=status.HTTP_400_BAD_REQUEST):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def _build_order_items(order, items, currency):
    """
    Create OrderItems using ONLY server-side (database) prices.

    SECURITY / INTEGRITY:
    - any client-supplied `price` is IGNORED, so a tampered cart cannot change
      what the customer is actually charged (prices come from CurrencyPrice rows);
    - quantities are clamped to 1..99, and duplicate lines for the same
      product/size are merged BEFORE the stock check so two lines of "1" can't
      slip past a stock of 1;
    - the price must exist for the EXACT requested currency (`get_price_exact`),
      never a fallback to a different currency's amount.

    Raises _CheckoutError on any invalid/oversold line. Returns the Decimal
    subtotal computed from the database. Call inside transaction.atomic().
    """
    if not isinstance(items, list) or not items:
        raise _CheckoutError('Your cart is empty.')

    # 1. Collapse duplicate lines so stock is validated against the true total.
    merged = {}  # (product_id, size) -> quantity
    for item in items:
        if not isinstance(item, dict):
            raise _CheckoutError('Invalid cart item.')
        product_id = item.get('product_id') or (item.get('product') or {}).get('id')
        try:
            product_id = int(product_id)
        except (TypeError, ValueError):
            raise _CheckoutError('Invalid product in cart.')

        try:
            qty = int(item.get('quantity', 1))
        except (TypeError, ValueError):
            qty = 1
        qty = max(1, min(qty, 99))

        size = (item.get('selectedSize') or item.get('size') or '')[:50]
        key = (product_id, size)
        total_line_qty = merged.get(key, 0) + qty
        if total_line_qty > 99:
            raise _CheckoutError('You can order at most 99 units of an item.')
        merged[key] = total_line_qty

    # 2. Load every referenced product once and validate stock up-front.
    product_ids = {pid for pid, _size in merged}
    products = {p.id: p for p in Product.objects.prefetch_related('prices').filter(id__in=product_ids)}
    if product_ids - products.keys():
        raise _CheckoutError('One of the products in your cart no longer exists.')

    qty_per_product = {}
    for (pid, _size), qty in merged.items():
        qty_per_product[pid] = qty_per_product.get(pid, 0) + qty
    for pid, total_qty in qty_per_product.items():
        product = products[pid]
        if (product.stock or 0) < total_qty:
            raise _CheckoutError(f'Sorry, only {product.stock} x "{product.name}" left in stock.')

    # 3. Persist the lines with prices read from the DATABASE (client price ignored).
    subtotal = Decimal('0.00')
    for (pid, size), qty in merged.items():
        product = products[pid]
        db_price = product.get_price_exact(currency)
        if db_price is None:
            raise _CheckoutError(
                f'"{product.name}" is not available in {currency}. Please choose another currency.'
            )
        unit_price = Decimal(str(db_price))
        if unit_price <= 0:
            raise _CheckoutError(f'"{product.name}" has an invalid price. Please contact support.')

        OrderItem.objects.create(
            order=order,
            product=product,
            product_name=product.name,
            size=size,
            price=unit_price,     # server-side price only
            quantity=qty,
        )
        subtotal += unit_price * qty
    return subtotal


def _delivery_fee(currency, amount_sek=DELIVERY_FEE_SEK):
    """Convert a SEK delivery fee to the order's selected currency."""
    target = (currency or 'EUR').upper()
    if target not in RATES_TO_USD:
        raise _CheckoutError('Unsupported delivery currency.')
    amount = Decimal(str(amount_sek)) * RATES_TO_USD['SEK'] / RATES_TO_USD[target]
    return amount.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


def _order_delivery_fee(order, currency):
    """Charge the highest effective product fee once for the entire order."""
    fees = []
    for item in order.items.select_related('product'):
        fees.append(
            item.product.delivery_fee_sek
            if item.product and item.product.delivery_fee_sek is not None
            else DELIVERY_FEE_SEK
        )
    return _delivery_fee(currency, max(fees)) if fees else Decimal('0.00')


def _reserve_stock(order):
    """
    Atomically decrement stock for every line on `order` — at most once per line.

    CONCURRENCY: each line is a single conditional UPDATE
    (`WHERE id = ? AND stock >= quantity` with `stock = stock - quantity`). The
    database evaluates the stock check and the decrement as ONE atomic operation,
    so when two buyers race for the last unit exactly one row is updated and the
    other updates 0 rows. This eliminates the classic read-modify-write oversell
    without relying on SELECT ... FOR UPDATE.

    Raises _CheckoutError if any line can no longer be fulfilled. Always call
    inside transaction.atomic() so that a later failing line rolls back the
    decrements already made for earlier lines.
    """
    for item in order.items.select_related('product'):
        updated = Product.objects.filter(
            pk=item.product_id, stock__gte=item.quantity
        ).update(stock=F('stock') - item.quantity)
        if not updated:
            product = Product.objects.get(pk=item.product_id)
            raise _CheckoutError(f'Sorry, "{product.name}" just went out of stock.')


def _release_stock(order):
    """
    Put stock back for every line on `order` — at most once for the order.

    Mirrors _reserve_stock: a conditional UPDATE on Order first *claims* the
    release (`WHERE id = ? AND stock_released = false`). Whoever flips the flag
    increments the product rows, so a retried `charge.refunded` webhook, a
    duplicate refund click, or a concurrent cancellation cannot inflate stock
    above what was actually sold.

    Returns True if this call performed the release.
    """
    with transaction.atomic():
        claimed = Order.objects.filter(pk=order.pk, stock_released=False).update(stock_released=True)
        if not claimed:
            return False  # already released by another caller

        for item in order.items.select_related('product').only('product_id', 'quantity'):
            Product.objects.filter(pk=item.product_id).update(stock=F('stock') + item.quantity)

        logger.info('Released stock for order %s', order.pk)
        return True


def _mark_paid_and_reserve(order):
    """
    Idempotently transition `order` to paid and consume stock EXACTLY ONCE.

    The `is_paid = True` transition is a single conditional UPDATE
    (`WHERE id = ? AND is_paid = false`). That makes the whole operation safe to
    run concurrently: if confirm_checkout and the Stripe webhook fire at the same
    moment, only the caller that "claims" the unpaid row proceeds, so stock is
    never decremented twice.

    Returns True if this call performed the transition, False if another caller
    had already done so.
    """
    with transaction.atomic():
        claimed = Order.objects.filter(pk=order.pk, is_paid=False).update(is_paid=True)
        if not claimed:
            return False  # another caller already handled this payment
        try:
            _reserve_stock(order)
        except _CheckoutError as exc:
            # Payment captured but the item sold out during the payment window.
            # The order stays paid (the customer was charged) so the merchant can
            # refund/backorder; logged for manual follow-up rather than oversold.
            logger.error('Oversold at payment capture (order id %s): %s', order.pk, exc.message)
        transaction.on_commit(lambda order_id=order.pk: _notify_paid_customer(order_id))
        return True


def _notify_paid_customer(order_id):
    """Send the paid-order receipt after payment state and stock commit."""
    try:
        order = Order.objects.get(pk=order_id)
        notifications.notify_customer(order, event='paid')
    except Exception:
        logger.exception('Paid receipt dispatch failed for order %s', order_id)


@api_view(['GET', 'POST'])
@permission_classes([AllowAny])
def facebook_webhook(request):
    """
    Meta Page webhook that drives the Facebook product sync.

    GET — the one-time URL verification Meta performs when the
          endpoint is registered (hub.mode=subscribe,
          hub.verify_token, hub.challenge). The challenge is echoed
          back as plain text, which proves we control the URL.

    POST — `feed` changes: a post was added, edited or removed on
          the Page. Each change is applied through products.facebook,
          matched idempotently on the Graph API post id, so Meta's
          automatic retries are harmless.

    The handler never raises: Meta retries non-2xx answers for
    days, so a malformed payload is answered 200 and logged.
    """
    if request.method == 'GET':
        challenge = facebook.verify_webhook_request(request.query_params)
        if challenge is None:
            return Response({'error': 'Webhook verification failed.'},
                            status=status.HTTP_403_FORBIDDEN)
        # Meta expects the raw challenge value, not a JSON body.
        return HttpResponse(challenge, content_type='text/plain')

    if not facebook.verify_signature(request.body,
                                     request.META.get('HTTP_X_HUB_SIGNATURE_256', '')):
        return Response({'error': 'Invalid webhook signature.'},
                        status=status.HTTP_403_FORBIDDEN)

    payload = request.data if isinstance(request.data, dict) else {}
    results = []
    try:
        for entry in payload.get('entry') or []:
            if not isinstance(entry, dict):
                continue
            for change in entry.get('changes') or []:
                if not isinstance(change, dict) or change.get('field') != 'feed':
                    continue
                results.append(facebook.handle_feed_change(change.get('value') or {}))
    except Exception:
        logger.exception('Facebook webhook processing failed')
    return Response({'received': True, 'results': results})


@api_view(['GET'])
@permission_classes([AllowAny])
def site_settings(request):
    payload = SiteSettingsSerializer(SiteSettings.get(), context={'request': request}).data
    # One round-trip for the storefront: payment/social links above, plus the
    # email-marketing consent row that decides whether the footer form and the
    # checkout opt-in checkbox render at all.
    payload['newsletter'] = CustomerNotificationSettingsSerializer(CustomerNotificationSettings.get()).data
    return Response(payload)


@api_view(['POST'])
@permission_classes([AllowAny])
@throttle_classes([NewsletterThrottle])
def newsletter_subscribe(request):
    """Storefront footer sign-up: forward the address to the shop mailbox.

    The admin-controlled consent row gates this endpoint too — pausing sign-ups
    in the admin stops capture immediately, with no deploy.
    """
    prefs = CustomerNotificationSettings.get()
    if not prefs.signup_enabled or prefs.status != 'active':
        return Response({'error': 'Email sign-ups are paused right now.'},
                        status=status.HTTP_400_BAD_REQUEST)
    if not prefs.recipient_email:
        return Response({'error': 'Email sign-ups are not configured yet.'},
                        status=status.HTTP_400_BAD_REQUEST)

    from django.core.exceptions import ValidationError as DjangoValidationError
    from django.core.validators import validate_email
    email = str(request.data.get('email') or '').strip().lower()
    try:
        validate_email(email)
    except DjangoValidationError:
        return Response({'error': 'Please provide a valid email address.'},
                        status=status.HTTP_400_BAD_REQUEST)

    from django.core.mail import send_mail
    try:
        send_mail(
            subject='New newsletter sign-up — Maims',
            message=f'A new address joined the mailing list from the storefront footer:\n\n'
                    f'{email}\n',
            from_email=None,
            recipient_list=[prefs.recipient_email],
            fail_silently=False,
        )
    except Exception:
        # Never leak transport details (SMTP credentials, hostnames) to the client.
        logger.exception('Newsletter sign-up email failed')
        return Response({'error': 'Could not save your address. Please try again later.'},
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    return Response({'ok': True}, status=status.HTTP_201_CREATED)

def _as_bool(value):
    """Coerce the checkbox/JSON value the client sent into a real boolean."""
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in ('true', '1', 'yes', 'on')


def _checkout_response_payload(order):
    """Build the response body for an order that already exists."""
    payload = {
        'order_id': order.id,
        'payment_method': order.payment_method,
        'order': OrderSerializer(order).data,
    }
    if order.payment_method == 'whatsapp':
        store = SiteSettings.get()
        lines = [
            f"{it.quantity} x {it.product.name}" + (f" ({it.size})" if it.size else "")
            for it in order.items.all()
        ]
        msg = (
            f"{store.whatsapp_greeting or 'Hello! I want to order:'}\n"
            + "\n".join(lines)
            + f"\nTotal: {order.total_amount} {order.currency}"
            + f"\nOrder #{order.id} - {order.first_name} {order.last_name}, "
              f"{order.address}, {order.zipcode} {order.place}"
        )
        payload['whatsapp_link'] = store.whatsapp_link(msg)
    return payload


def _checkout_replay_response(order):
    """
    Answer a checkout replay with HTTP 200 — the work already happened, so this is
    not a failure. The body is shaped exactly like the original response so the
    frontend's normal success path runs unchanged.
    """
    payload = _checkout_response_payload(order)
    payload['replayed'] = True

    if order.payment_method == 'stripe':
        # The retry still has to be able to finish paying, so hand back the live
        # client_secret of the PaymentIntent the first attempt created.
        if not order.stripe_payment_intent_id:
            return Response(
                {'error': 'A previous checkout for this request never reached payment. Please try again.'},
                status=status.HTTP_409_CONFLICT,
            )
        try:
            intent = stripe.PaymentIntent.retrieve(order.stripe_payment_intent_id)
        except Exception:
            logger.exception('Could not re-fetch PaymentIntent for order %s', order.pk)
            return Response(
                {'error': 'Unable to resume this payment. Please try again.'},
                status=status.HTTP_409_CONFLICT,
            )
        payload['client_secret'] = intent.client_secret

    return Response(payload, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([AllowAny])
@throttle_classes([CheckoutThrottle])
def checkout(request):
    """
    Unified checkout: payment_method = stripe | paypal | whatsapp.

    SECURITY: the order total and every unit price are derived from the database
    only — the client's `total_amount` / `price` are never trusted.
    - stripe: PaymentIntent, order unpaid until confirm/webhook.
    - paypal: order created unpaid; the customer completes payment on PayPal and
      the order is marked paid once PayPal confirms it.
    - whatsapp: order created immediately, stock reserved at once; payment is
      arranged in the WhatsApp thread.

    IDEMPOTENCY: send an `Idempotency-Key` header (the frontend generates one per
    checkout attempt). A repeated POST carrying a key that already produced an
    order returns that same order instead of creating a second one, so a
    double-click, a retried fetch or a refresh mid-redirect cannot double-charge
    the customer or double-decrement stock. The same key is forwarded to Stripe as
    the PaymentIntent idempotency key.
    """

    # --- Replay protection ---------------------------------------------------
    # Long enough for a retry loop, short enough that it cannot collide with a
    # later, genuinely new order. Headers are untrusted, so bound the length.
    checkout_key = (request.META.get('HTTP_IDEMPOTENCY_KEY') or '').strip()[:64] or None

    data = request.data
    payment_method = str(data.get('payment_method') or 'stripe').lower()
    if payment_method not in ('stripe', 'paypal', 'whatsapp'):
        return Response({'error': 'Invalid payment method.'}, status=status.HTTP_400_BAD_REQUEST)

    store = SiteSettings.get()
    if payment_method == 'paypal' and not store.paypal_enabled:
        return Response({'error': 'PayPal is currently disabled.'}, status=status.HTTP_400_BAD_REQUEST)
    if payment_method == 'whatsapp' and not (store.whatsapp_enabled and store.whatsapp_number):
        return Response({'error': 'WhatsApp ordering is not configured yet.'}, status=status.HTTP_400_BAD_REQUEST)
    if payment_method == 'stripe' and not store.stripe_enabled:
        return Response({'error': 'Card payments are currently disabled.'}, status=status.HTTP_400_BAD_REQUEST)
    if payment_method == 'stripe' and not settings.STRIPE_SECRET_KEY:
        return Response({'error': 'Card payments are not configured.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    # Validate required fields (pricing is never taken from the client).
    # Phone is collected by default: every channel the shop uses to reach a
    # customer (confirmation email, WhatsApp updates, courier delivery)
    # needs it, so an order without one is rejected here.
    if not data.get('items'):
        return Response({'error': 'Your cart is empty.'}, status=status.HTTP_400_BAD_REQUEST)
    for field in ('first_name', 'last_name', 'email', 'phone', 'address', 'zipcode', 'place'):
        if not data.get(field):
            return Response({'error': f'Please provide {field.replace("_", " ")}.'},
                            status=status.HTTP_400_BAD_REQUEST)

    # Normalize currency: frontend sends EUR/PKR/USD/SEK/BDT, Stripe needs lowercase.
    raw_currency = str(data.get('currency') or 'EUR').upper()
    stripe_currency = raw_currency.lower()
    if stripe_currency not in ('eur', 'usd', 'sek', 'bdt', 'pkr'):
        raw_currency = 'EUR'
        stripe_currency = 'eur'

    order_user = request.user if request.user.is_authenticated else None

    # A retried request with the same key must resolve to the original order.
    # Checked after the cheap field validation but before any write or stock
    # reservation. `checkout_key` is globally unique, so the key is first matched
    # against the caller's own orders; a key that belongs to somebody else is
    # never honoured (that would leak their address and email) and is dropped so
    # this caller still gets their own order instead of a constraint crash.
    replay_order = None
    if checkout_key:
        scope = Q(user=order_user) if order_user else Q(user__isnull=True)
        key_taken = Order.objects.filter(checkout_key=checkout_key)
        replay_order = (
            key_taken.filter(scope)
            .prefetch_related(Prefetch('items', queryset=OrderItem.objects.select_related('product')))
            .first()
        )
        if replay_order is not None:
            logger.info('Replayed checkout for key %s resolved to order %s',
                        checkout_key, replay_order.pk)
            return _checkout_replay_response(replay_order)

        if key_taken.exists():
            # Someone else's order holds this key. Play it safe: proceed with a
            # fresh order rather than reusing or exposing theirs.
            logger.warning('Checkout key already in use by another customer; '
                           'proceeding without idempotency')
            checkout_key = None

    try:
        # The whole write (order + lines + stock reservation) is atomic: if any
        # step fails, nothing is persisted and no stock is consumed.
        with transaction.atomic():
            # 1. Persist the order with a placeholder total; the authoritative
            #    total is computed server-side from the database below.
            # Marketing consent is only stored when the shop would still be
            # showing the checkbox at submit time — if settings changed between
            # page load and POST, the admin's choice wins and no consent that
            # the UI wouldn't have offered is recorded.
            prefs = CustomerNotificationSettings.get()
            marketing_consent = (
                _as_bool(data.get('marketing_opt_in'))
                and prefs.checkout_opt_in_enabled
                and prefs.accepts_signups
            )
            order = Order.objects.create(
                user=order_user,
                first_name=data['first_name'],
                last_name=data['last_name'],
                email=data['email'],
                phone=data.get('phone', ''),
                address=data['address'],
                zipcode=data['zipcode'],
                place=data['place'],
                total_amount=Decimal('0.00'),
                currency=raw_currency,
                payment_method=payment_method,
                is_paid=False,
                checkout_key=checkout_key,
                # WhatsApp only allows business-initiated messages to people who
                # asked for them, so the customer's choice is stored with the
                # order and re-checked by the notifier before every send.
                whatsapp_opt_in=_as_bool(data.get('whatsapp_opt_in')),
                marketing_opt_in=marketing_consent,
            )

            subtotal = _build_order_items(order, data.get('items', []), raw_currency)
            if subtotal <= 0:
                raise _CheckoutError('Cart total must be greater than zero.')
            order.delivery_fee = _order_delivery_fee(order, raw_currency)
            order.total_amount = subtotal + order.delivery_fee

            # PayPal / WhatsApp: no Stripe intent — the order is created unpaid
            # and stock is reserved atomically right now. PayPal is captured
            # later (manually by the shop until a PayPal client ID exists).
            if payment_method in ('paypal', 'whatsapp'):
                _reserve_stock(order)
                order.save(update_fields=['total_amount', 'delivery_fee'])
                payload = _checkout_response_payload(order)
                # Customer/admin notifications are dispatched by the post_save
                # signal on Order, which defers to on_commit internally — so they
                # only go out once this transaction actually commits.
                return Response(payload, status=status.HTTP_201_CREATED)

            order.save(update_fields=['total_amount', 'delivery_fee'])

        # 2. Stripe: charge the SERVER-computed total, including delivery.
        #    Run outside the DB transaction so a slow Stripe call never holds locks.
        amount_in_cents = int((order.total_amount * 100).quantize(Decimal('1'), rounding=ROUND_HALF_UP))
        intent_kwargs = {
            'amount': amount_in_cents,
            'currency': stripe_currency,
            'automatic_payment_methods': {'enabled': True},
            'receipt_email': data.get('email'),
            'metadata': {'customer_email': data.get('email'), 'currency': raw_currency,
                         'order_id': order.id},
        }
        # Belt and braces with `checkout_key`: if this request is retried after
        # the order row was created but the response never reached the client,
        # Stripe returns the ORIGINAL intent instead of creating and charging a
        # second one.
        intent = stripe.PaymentIntent.create(
            idempotency_key=f'order-{order.pk}' if checkout_key else None,
            **intent_kwargs,
        )
        order.stripe_payment_intent_id = intent.id
        order.save(update_fields=['stripe_payment_intent_id'])

        return Response({
            'client_secret': intent.client_secret,
            'order_id': order.id
        }, status=status.HTTP_201_CREATED)

    except _CheckoutError as e:
        return Response({'error': e.message}, status=e.status_code)
    except Exception:
        # Log the traceback server-side for diagnosis; never the message, which
        # can contain secrets or payment data. A server fault is a 5xx, not a
        # 4xx — the client's request was fine and retrying may well succeed.
        logger.exception('Checkout failed')
        return Response(
            {'error': 'Something went wrong processing your checkout on the server.'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['GET', 'PUT'])
@permission_classes([IsAuthenticated]) # 🌟 Only logged-in users can touch this endpoint
def my_profile(request):
    profile, created = UserProfile.objects.get_or_create(user=request.user)

    if request.method == 'GET':
        serializer = UserProfileSerializer(profile)
        return Response(serializer.data)

    elif request.method == 'PUT':
        # Allow first_name / last_name edits: they live on User, not UserProfile.
        user = request.user
        updated_user_fields = []
        for field in ('first_name', 'last_name'):
            if field in request.data:
                setattr(user, field, (request.data.get(field) or '').strip())
                updated_user_fields.append(field)
        if updated_user_fields:
            user.save(update_fields=updated_user_fields)
        # partial=True allows them to update just one field (like just phone) without breaking
        serializer = UserProfileSerializer(profile, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([AllowAny])
@throttle_classes([AuthThrottle])
def register_user(request):
    """Create account -> return {token, user}. Validates via RegisterSerializer."""
    serializer = RegisterSerializer(data=request.data)
    if not serializer.is_valid():
        # Flatten to a single friendly message + keep field details.
        first_error = next(
            (str(msgs[0]) for msgs in serializer.errors.values() if msgs),
            'Please check your details and try again.'
        )
        return Response(
            {'error': first_error, 'errors': serializer.errors},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        user = serializer.save()
        token, _ = Token.objects.get_or_create(user=user)
        UserProfile.objects.get_or_create(user=user)
        return Response({
            'token': token.key,
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
            },
            # Back-compat for existing frontend code:
            'username': user.username,
        }, status=status.HTTP_201_CREATED)
    except Exception:
        # Log only the error class — never the message (can contain secrets/PII).
        logger.exception('Registration failed')
        return Response({'error': 'Failed to create user.'}, status=status.HTTP_400_BAD_REQUEST)


# --- PASSWORD RESET ---------------------------------------------------------------------

@api_view(['POST'])
@permission_classes([AllowAny])
@throttle_classes([AuthThrottle])
def password_reset_request(request):
    """
    Email a one-time password-reset link to the account's address.

    The response is identical whether or not the address is registered,
    so the endpoint cannot be used to enumerate customer emails.
    """
    email = str(request.data.get('email') or '').strip().lower()
    if not email:
        return Response({'error': 'Please provide your email address.'},
                        status=status.HTTP_400_BAD_REQUEST)

    user = User.objects.filter(email__iexact=email).first()
    if user:
        token = default_token_generator.make_token(user)
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        reset_url = (
            f"{settings.FRONTEND_BASE_URL}/reset-password"
            f"?uid={uid}&token={token}"
        )
        subject = '[Maims] Reset your password'
        message = (
            f"Hello {user.first_name or user.username},\n\n"
            "Someone (hopefully you) asked to reset the password for your "
            "Maims account.\n"
            "Open this link to choose a new one — it stays valid for the "
            f"next 24 hours:\n\n"
            f"{reset_url}\n\n"
            "If you did not ask for this, simply ignore this email; your "
            "password is unchanged.\n\n"
            "— Maims"
        )
        try:
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL or None,
                recipient_list=[user.email],
                fail_silently=False,
            )
        except Exception:
            # Never leak delivery problems to the caller; the generic
            # reply below is correct either way, and the traceback is in
            # the server logs for the shop to investigate.
            logger.exception('Password reset email failed for user %s', user.pk)

    return Response({
        'detail': 'If an account with that email exists, a reset link is on its way.'
    })


@api_view(['POST'])
@permission_classes([AllowAny])
@throttle_classes([AuthThrottle])
def password_reset_confirm(request):
    """Validate the emailed token and set a new password."""
    uid = str(request.data.get('uid') or '')
    token = str(request.data.get('token') or '')
    new_password = request.data.get('new_password')

    if not uid or not token or not new_password:
        return Response({'error': 'Missing reset details.'},
                        status=status.HTTP_400_BAD_REQUEST)

    try:
        user_id = urlsafe_base64_decode(uid).decode()
        user = User.objects.get(pk=user_id)
    except (TypeError, ValueError, OverflowError, binascii.Error, User.DoesNotExist):
        return Response({'error': 'This reset link is invalid.'},
                        status=status.HTTP_400_BAD_REQUEST)

    if not default_token_generator.check_token(user, token):
        return Response({'error': 'This reset link has expired or is invalid.'},
                        status=status.HTTP_400_BAD_REQUEST)

    # The same rules as sign-up: length, similarity to the user's data,
    # common-password checks, ...
    try:
        validate_password(new_password, user)
    except ValidationError as exc:
        return Response({'error': ' '.join(exc.messages)},
                        status=status.HTTP_400_BAD_REQUEST)

    user.set_password(new_password)
    user.save()
    return Response({
        'detail': 'Password updated. You can log in with your new password.'
    })


@api_view(['POST'])
@permission_classes([AllowAny])
@throttle_classes([AuthThrottle])
def login_user(request):
    """Login with username OR email + password -> {token, user}."""
    from django.contrib.auth import authenticate
    identifier = (request.data.get('username') or request.data.get('email') or '').strip()
    password = request.data.get('password') or ''

    if not identifier or not password:
        return Response(
            {'error': 'Please provide your username (or email) and password.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Allow email login: resolve email -> username.
    username = identifier
    if '@' in identifier:
        try:
            username = User.objects.get(email__iexact=identifier).username
        except User.DoesNotExist:
            return Response(
                {'error': 'Unable to log in with provided credentials.'},
                status=status.HTTP_400_BAD_REQUEST
            )

    user = authenticate(username=username, password=password)
    if user is None:
        return Response(
            {'error': 'Unable to log in with provided credentials.'},
            status=status.HTTP_400_BAD_REQUEST
        )
    if not user.is_active:
        return Response(
            {'error': 'This account has been disabled.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    token, _ = Token.objects.get_or_create(user=user)
    return Response({
        'token': token.key,
        'user': {
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
        },
    }, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout_user(request):
    """Delete the current token so this device is logged out."""
    try:
        request.auth.delete()
    except Exception:
        Token.objects.filter(user=request.user).delete()
    return Response({'message': 'Logged out successfully.'})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def me(request):
    """Return the logged-in user + profile (single call for the frontend store)."""
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    return Response({
        'user': UserSerializer(request.user).data,
        'profile': UserProfileSerializer(profile).data,
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AuthThrottle])
def change_password(request):
    """Change password while logged in: {current_password, new_password}."""
    from django.contrib.auth.password_validation import validate_password
    current = request.data.get('current_password') or ''
    new = request.data.get('new_password') or ''
    if not request.user.check_password(current):
        return Response({'error': 'Your current password is incorrect.'}, status=status.HTTP_400_BAD_REQUEST)
    try:
        validate_password(new, request.user)
    except Exception as exc:
        msgs = getattr(exc, 'messages', [str(exc)])
        return Response({'error': '; '.join(msgs)}, status=status.HTTP_400_BAD_REQUEST)
    request.user.set_password(new)
    request.user.save()
    # Keep this device logged in with a fresh token; other devices keep old tokens.
    Token.objects.filter(user=request.user).delete()
    token = Token.objects.create(user=request.user)
    return Response({'message': 'Password changed successfully.', 'token': token.key})

# 🌟 ADD THIS NEW FUNCTION AT THE BOTTOM
@api_view(['GET'])
@permission_classes([IsAuthenticated])  # Only logged-in users can view their history
def get_orders(request):
    # Fetch only the orders that belong to the currently logged-in user, newest first.
    # OrderSerializer nests a full ProductSerializer per line, and that touches the
    # product's prices, media and category (plus the category's children and product
    # count). Left lazy, every one of those is a separate query per line, so a
    # customer with 20 past orders issued ~60 queries to render one page. These
    # joins collapse the whole history into a fixed handful without changing the
    # payload the frontend receives.
    orders = (
        Order.objects
        .filter(user=request.user)
        .select_related('user')
        .prefetch_related(
            # Prefetching 'items__product' (rather than annotating the OrderItem)
            # is deliberate: the nested ProductSerializer renders `item.product`,
            # and select_related builds that product as a fresh, un-annotated
            # instance per row. This prefetch replaces those instances with one
            # annotated copy each, which is what makes the star rating free.
            # It also de-duplicates the product rows, so a basket with the same
            # shirt in two orders is fetched once.
            Prefetch(
                'items__product',
                queryset=(
                    Product.objects
                    .annotate(
                        rating_average=Avg('reviews__rating', filter=Q(reviews__is_approved=True)),
                        rating_count=Count('reviews', distinct=True, filter=Q(reviews__is_approved=True)),
                    )
                    .prefetch_related(
                        'prices',
                        'media',
                        Prefetch(
                            'category',
                            queryset=(
                                Category.objects
                                .annotate(product_count=Count('products'))
                                .prefetch_related('children')
                            ),
                        ),
                    )
                ),
            ),
        )
        .order_by('-id')
    )

    serializer = OrderSerializer(orders, many=True)

    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([AllowAny])
def stripe_key(request):
    publishable_key = STRIPE_PUBLISHABLE_KEY
    if not publishable_key:
        return Response({'error': 'Stripe publishable key not configured.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    return Response({'publishableKey': publishable_key})


@api_view(['POST'])
@permission_classes([AllowAny])
@throttle_classes([CheckoutThrottle])
def confirm_checkout(request):
    order_id = request.data.get('order_id')
    payment_intent_id = request.data.get('payment_intent_id')

    if not order_id or not payment_intent_id:
        return Response({'error': 'Missing order_id or payment_intent_id.'}, status=status.HTTP_400_BAD_REQUEST)

    # IDOR GUARD: only the owner may confirm an order. A logged-in caller must
    # own the order (or it is an unclaimed guest order they just created); an
    # anonymous caller may only confirm an unclaimed guest order. Without this,
    # any user could pull another user's order (full PII) by changing order_id.
    qs = Order.objects.filter(id=order_id, stripe_payment_intent_id=payment_intent_id)
    if request.user.is_authenticated:
        qs = qs.filter(Q(user=request.user) | Q(user__isnull=True))
    else:
        qs = qs.filter(user__isnull=True)

    order = qs.first()
    if order is None:
        return Response({'error': 'Order not found.'}, status=status.HTTP_404_NOT_FOUND)

    # Idempotent: never mark paid / decrement stock twice for the same order.
    if order.is_paid:
        return Response({'order': OrderSerializer(order).data})

    try:
        intent = stripe.PaymentIntent.retrieve(payment_intent_id)
    except Exception:
        # Do not echo provider error details back to the client.
        return Response({'error': 'Unable to retrieve payment status.'}, status=status.HTTP_400_BAD_REQUEST)

    if intent.status == 'succeeded':
        # Atomically flip is_paid and consume stock exactly once (safe even if
        # the Stripe webhook fires at the same instant).
        _mark_paid_and_reserve(order)
        order.refresh_from_db()
        return Response({'order': OrderSerializer(order).data})

    return Response({'error': 'Payment has not completed.', 'status': intent.status}, status=status.HTTP_400_BAD_REQUEST)


def _prepend_note(order, note):
    """Build an internal note that keeps whatever the staff had already written."""
    existing = (order.admin_note or '').strip()
    return f'{note}\n{existing}' if existing else note


@api_view(['POST'])
@permission_classes([AllowAny])
def stripe_webhook(request):
    """
    Stripe webhook: final source of truth for card payments.

    SECURITY: signature verification is MANDATORY. If STRIPE_WEBHOOK_SECRET is
    not configured we refuse the request rather than accepting an unsigned JSON
    payload (which would let anyone forge `payment_intent.succeeded` and mark
    orders as paid for free).

    Handled events:
    - payment_intent.succeeded  -> mark paid + reserve stock (once)
    - payment_intent.payment_failed -> cancel the unpaid order
    - charge.refunded / charge.dispute.created -> release stock back (once)

    Every branch is keyed off an atomic conditional UPDATE, so Stripe's automatic
    retries (it retries for up to 3 days) can never double-count.
    """
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE', '')
    webhook_secret = settings.STRIPE_WEBHOOK_SECRET
    if not webhook_secret:
        return Response({'error': 'Webhook secret not configured.'},
                        status=status.HTTP_503_SERVICE_UNAVAILABLE)
    try:
        event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
    except Exception:
        return Response({'error': 'Invalid webhook signature.'}, status=status.HTTP_400_BAD_REQUEST)

    event_type = event.get('type', '')
    obj = (event.get('data') or {}).get('object') or {}

    # `payment_intent.*` events carry the intent as the object; charge-level
    # events (refund, dispute) reference it instead, so pick the right field per
    # event rather than always reading obj['id'].
    if event_type.startswith('charge.'):
        intent_id = obj.get('payment_intent')
    else:
        intent_id = obj.get('id')

    if not intent_id:
        return Response({'received': True})

    try:
        order = Order.objects.get(stripe_payment_intent_id=intent_id)
    except Order.DoesNotExist:
        # An intent we never created (or an order since deleted). Acknowledge so
        # Stripe stops retrying; there is nothing for us to reconcile.
        logger.info('Webhook %s references unknown intent %s', event_type, intent_id)
        return Response({'received': True})

    if event_type == 'payment_intent.succeeded':
        # Idempotent + concurrency-safe: only the caller that claims the unpaid
        # order consumes stock, so webhook retries / races with confirm_checkout
        # can never double-decrement inventory.
        if _mark_paid_and_reserve(order):
            logger.info('Order %s marked paid via webhook', order.pk)

    elif event_type == 'payment_intent.payment_failed':
        # The customer never completed payment, so nothing was ever reserved.
        # Just close the order so it does not sit in the "new" queue forever.
        updated = Order.objects.filter(pk=order.pk, is_paid=False).exclude(status='cancelled').update(
            status='cancelled',
            admin_note=_prepend_note(order, 'Card payment failed.'),
        )
        if updated:
            logger.info('Order %s cancelled after failed payment', order.pk)

    elif event_type in ('charge.refunded', 'charge.dispute.created'):
        # Only orders we actually charged and reserved stock for are restocked;
        # a refund on a cash-on-delivery order would create phantom inventory.
        if not order.is_paid:
            return Response({'received': True})
        if _release_stock(order):
            Order.objects.filter(pk=order.pk).update(
                status='returned',
                is_paid=False,
                admin_note=_prepend_note(order, 'Refunded via Stripe.'),
            )
            logger.info('Order %s marked refunded and stock released', order.pk)

    return Response({'received': True})


# --- REVIEWS ---

class ProductReviewList(APIView):
    """
    GET  /api/v1/products/<slug>/reviews/  published reviews for a product
    POST                            the same URL: write a review (login required)
    """

    permission_classes = [AllowAny]
    throttle_classes = [AuthThrottle]

    def get_object(self, slug):
        # Slugs are unique now, so .get() cannot raise MultipleObjectsReturned.
        return Product.objects.get(slug=slug, is_visible=True)

    def get(self, request, slug):
        try:
            product = self.get_object(slug)
        except Product.DoesNotExist:
            raise Http404

        reviews = (
            Review.objects
            .filter(product=product, is_approved=True)
            .select_related('user', 'order')
        )
        # Star breakdown for the "5 stars — 12" filter row.
        breakdown = (
            reviews.values('rating')
            .annotate(count=Count('id'))
            .order_by('-rating')
        )
        counts = {row['rating']: row['count'] for row in breakdown}

        serializer = ReviewSerializer(reviews, many=True)
        return Response({
            'reviews': serializer.data,
            'average_rating': product.average_rating,
            'review_count': product.review_count,
            'breakdown': {str(star): counts.get(star, 0) for star in range(1, 6)},
        })

    def post(self, request, slug):
        if not request.user.is_authenticated:
            return Response({'error': 'Please sign in to leave a review.'},
                            status=status.HTTP_401_UNAUTHORIZED)

        try:
            product = self.get_object(slug)
        except Product.DoesNotExist:
            raise Http404

        serializer = ReviewCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({'error': 'Please check your review.',
                             'errors': serializer.errors},
                            status=status.HTTP_400_BAD_REQUEST)

        # One review per customer per product. Updating is friendlier than a hard
        # 400 when someone genuinely wants to correct their rating.
        existing = Review.objects.filter(product=product, user=request.user).first()
        if existing and not request.data.get('force_update'):
            return Response(
                {'error': 'You have already reviewed this product. '
                          'Send force_update=true to change your existing review.'},
                status=status.HTTP_409_CONFLICT,
            )

        data = serializer.validated_data
        # Verified purchase: only orders that actually reached the customer count.
        order = (
            Order.objects
            .filter(user=request.user, status='delivered',
                    items__product=product)
            .order_by('-created_at')
            .distinct()
            .first()
        )

        if existing:
            existing.rating = data['rating']
            existing.title = data['title']
            existing.comment = data['comment']
            # Re-verify on update: the reviewer may now own a delivered order.
            existing.order = order
            existing.is_approved = True
            existing.product_name_snapshot = product.name
            existing.save()
            return Response(ReviewSerializer(existing).data, status=status.HTTP_200_OK)

        review = Review.objects.create(
            product=product,
            user=request.user,
            order=order,
            rating=data['rating'],
            title=data['title'],
            comment=data['comment'],
            product_name_snapshot=product.name,
        )
        return Response(ReviewSerializer(review).data, status=status.HTTP_201_CREATED)


class ReviewDetail(APIView):
    """
    DELETE /api/v1/reviews/<id>/  withdraw your own review.

    IDOR GUARD: the lookup is scoped to the requesting user, so deleting another
    customer's review returns 404 rather than 403 — the API must not confirm that
    someone else's review id exists.
    """

    permission_classes = [IsAuthenticated]

    def delete(self, request, pk):
        deleted, _ = Review.objects.filter(pk=pk, user=request.user).delete()
        if not deleted:
            return Response({'error': 'Review not found.'},
                            status=status.HTTP_404_NOT_FOUND)
        return Response(status=status.HTTP_204_NO_CONTENT)
        return Response(status=status.HTTP_204_NO_CONTENT)


# --- WISHLIST ---

class WishlistList(APIView):
    """
    GET  /api/v1/wishlist/   the current user's saved products (newest first)
    POST /api/v1/wishlist/   save a product  { product_id: <id> }

    POST is idempotent: hearting a product that is already saved returns the
    existing row (200) instead of an error, so a double-tap or a retried
    request can never duplicate a row or surface a scary 409 to the customer.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        # select_related collapses user+product into one row; ProductSerializer
        # prefetches its own prices/media/category so the catalogue data is
        # complete without a per-item query on this side.
        items = WishlistItem.objects.filter(user=request.user).select_related('product')
        serializer = WishlistItemSerializer(items, many=True)
        return Response({'results': serializer.data, 'count': len(serializer.data)})

    def post(self, request):
        serializer = WishlistAddSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        product_id = serializer.validated_data['product_id']

        try:
            product = Product.objects.get(pk=product_id)
        except Product.DoesNotExist:
            return Response({'error': 'Product not found.'},
                            status=status.HTTP_404_NOT_FOUND)

        # Idempotent add: return the existing row when already saved.
        existing = WishlistItem.objects.filter(user=request.user, product=product).first()
        if existing:
            return Response(WishlistItemSerializer(existing).data,
                            status=status.HTTP_200_OK)

        item = WishlistItem.objects.create(user=request.user, product=product)
        return Response(WishlistItemSerializer(item).data,
                        status=status.HTTP_201_CREATED)


class WishlistDetail(APIView):
    """
    DELETE /api/v1/wishlist/<id>/  remove a saved product.

    IDOR GUARD: the lookup is scoped to the requesting user, so deleting another
    customer's wishlist row returns 404 rather than 403 — the API must not
    confirm that someone else's row id exists.
    """

    permission_classes = [IsAuthenticated]

    def delete(self, request, pk):
        deleted, _ = WishlistItem.objects.filter(pk=pk, user=request.user).delete()
        if not deleted:
            return Response({'error': 'Wishlist item not found.'},
                            status=status.HTTP_404_NOT_FOUND)
        return Response(status=status.HTTP_204_NO_CONTENT)


# --- Hero banner ---------------------------------------------------------------

@api_view(['GET'])
@permission_classes([AllowAny])
def hero_banner_settings(request):
    """Public read of the hero banner controls.

    The admin edits one row; every visitor reads it. No auth needed so the
    homepage renders before the customer is logged in.
    """
    settings = HeroBannerSettings.get()
    return Response(HeroBannerSettingsSerializer(settings).data)


# --- 🤖 AI CHATBOT AGENT VIEWS --------------------------------------------------

class ChatbotView(APIView):
    """
    POST /api/v1/chatbot/chat/
    Accepts: { "message": "...", "session_id": "...", "currency": "EUR" }
    Returns: { "reply": "...", "products": [...], "suggestions": [...], "action": {...} }
    """
    permission_classes = [AllowAny]
    throttle_classes = [ChatbotThrottle]

    def post(self, request):
        message = str(request.data.get('message') or '').strip()
        if not message:
            return Response({'error': 'Message cannot be empty.'}, status=status.HTTP_400_BAD_REQUEST)

        # Cap message length to prevent memory abuse
        if len(message) > 1000:
            message = message[:1000]

        session_id = str(request.data.get('session_id') or '').strip()[:64]
        currency = str(request.data.get('currency') or 'EUR').strip().upper()
        if currency not in ('EUR', 'USD', 'PKR', 'SEK', 'BDT'):
            currency = 'EUR'

        user = request.user if request.user and request.user.is_authenticated else None

        agent = ChatbotAgent(currency=currency, user=user, session_id=session_id)
        response_payload = agent.respond(message)

        return Response(response_payload, status=status.HTTP_200_OK)


class ChatbotSuggestionsView(APIView):
    """
    GET /api/v1/chatbot/suggestions/
    Returns initial quick-prompts and greeting for the storefront chat assistant.
    """
    permission_classes = [AllowAny]

    def get(self, request):
        store = SiteSettings.get()
        store_name = store.store_name or 'Maims'
        return Response({
            'store_name': store_name,
            'greeting': f"Hello and welcome to {store_name}! ✨ I am your personal AI shopping stylist and order assistant. How can I assist you today?",
            'suggestions': [
                "Show latest arrivals",
                "Pure silk sarees under €100",
                "Unstitched festive suits",
                "Track my order",
                "How long does shipping take?",
                "Chat on WhatsApp",
            ]
        })
