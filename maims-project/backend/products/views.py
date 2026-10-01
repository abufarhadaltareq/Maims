import stripe
import os
from decimal import Decimal, ROUND_HALF_UP
from django.conf import settings
from django.http import Http404
from rest_framework.views import APIView
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.throttling import SimpleRateThrottle
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth.models import User
from django.db import transaction
from django.db.models import Q, Count, Prefetch, F
from rest_framework.authtoken.models import Token
from .models import Category, CurrencyPrice, HeroSlide, Order, OrderItem, Product, SiteSettings, UserProfile
from .serializers import (
    CategorySerializer, HeroSlideSerializer, OrderSerializer, ProductSerializer, SiteSettingsSerializer,
    UserProfileSerializer,
    RegisterSerializer, UserSerializer,
)

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


# --- 🌟 RESTORED: PRODUCT VIEWS ---

def product_queryset():
    return Product.objects.select_related('category').prefetch_related(
        'prices', 'media', Prefetch('category__children')
    )


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

        serializer = ProductSerializer(products, many=True, context={'request': request})
        return Response(serializer.data)
    
class ProductDetail(APIView):
    """
    Handles fetching data for an individual product's detail page.
    """
    permission_classes = [AllowAny]

    def get(self, request, slug, format=None):
        try:
            product = product_queryset().get(slug=slug)
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
        ).annotate(product_count=Count('products', distinct=True))
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
    Homepage "Shop by Category" payload: each homepage-flagged category
    with up to 8 preview products (children products included).
    """
    permission_classes = [AllowAny]

    def get(self, request, format=None):
        from .models import Product as ProductModel
        cats = Category.objects.filter(
            parent__isnull=True, show_on_homepage=True
        ).prefetch_related('children').order_by('homepage_order', 'name')
        payload = []
        for cat in cats:
            child_ids = list(cat.children.values_list('id', flat=True))
            products = product_queryset().filter(
                Q(category=cat) | Q(category_id__in=child_ids)
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
            Q(category=category) | Q(category_id__in=child_ids)
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
            size=size,
            price=unit_price,     # server-side price only
            quantity=qty,
        )
        subtotal += unit_price * qty
    return subtotal


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
            print("Oversold at payment capture (order id):", order.pk, exc.message)
        return True


@api_view(['GET'])
@permission_classes([AllowAny])
def site_settings(request):
    return Response(SiteSettingsSerializer(SiteSettings.get()).data)

@api_view(['POST'])
@permission_classes([AllowAny])
@throttle_classes([CheckoutThrottle])
def checkout(request):
    """
    Unified checkout: payment_method = stripe | cod | whatsapp.

    SECURITY: the order total and every unit price are derived from the database
    only — the client's `total_amount` / `price` are never trusted.
    - stripe: PaymentIntent, order unpaid until confirm/webhook.
    - cod/whatsapp: order created immediately, stock reserved at once.
    """
    data = request.data
    payment_method = str(data.get('payment_method') or 'stripe').lower()
    if payment_method not in ('stripe', 'cod', 'whatsapp'):
        return Response({'error': 'Invalid payment method.'}, status=status.HTTP_400_BAD_REQUEST)

    store = SiteSettings.get()
    if payment_method == 'cod' and not store.cod_enabled:
        return Response({'error': 'Cash on Delivery is currently disabled.'}, status=status.HTTP_400_BAD_REQUEST)
    if payment_method == 'whatsapp' and not (store.whatsapp_enabled and store.whatsapp_number):
        return Response({'error': 'WhatsApp ordering is not configured yet.'}, status=status.HTTP_400_BAD_REQUEST)
    if payment_method == 'stripe' and not store.stripe_enabled:
        return Response({'error': 'Card payments are currently disabled.'}, status=status.HTTP_400_BAD_REQUEST)
    if payment_method == 'stripe' and not settings.STRIPE_SECRET_KEY:
        return Response({'error': 'Card payments are not configured.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    # Validate required fields (pricing is never taken from the client).
    if not data.get('items'):
        return Response({'error': 'Your cart is empty.'}, status=status.HTTP_400_BAD_REQUEST)
    for field in ('first_name', 'last_name', 'email', 'address', 'zipcode', 'place'):
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

    try:
        # The whole write (order + lines + stock reservation) is atomic: if any
        # step fails, nothing is persisted and no stock is consumed.
        with transaction.atomic():
            # 1. Persist the order with a placeholder total; the authoritative
            #    total is computed server-side from the database below.
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
            )

            subtotal = _build_order_items(order, data.get('items', []), raw_currency)
            if subtotal <= 0:
                raise _CheckoutError('Cart total must be greater than zero.')
            order.total_amount = subtotal

            # COD / WhatsApp: no Stripe — reserve stock atomically right now.
            if payment_method in ('cod', 'whatsapp'):
                _reserve_stock(order)
                order.save(update_fields=['total_amount'])
                payload = {'order_id': order.id, 'payment_method': payment_method,
                           'order': OrderSerializer(order).data}
                if payment_method == 'whatsapp':
                    lines = [f"{it.quantity} x {it.product.name}" + (f" ({it.size})" if it.size else "")
                             for it in order.items.all()]
                    msg = (f"{store.whatsapp_greeting or 'Hello! I want to order:'}\n" + "\n".join(lines) +
                           f"\nTotal: {order.total_amount} {order.currency}\nOrder #{order.id} - {order.first_name} {order.last_name}, {order.address}, {order.zipcode} {order.place}")
                    payload['whatsapp_link'] = store.whatsapp_link(msg)
                return Response(payload, status=status.HTTP_201_CREATED)

            order.save(update_fields=['total_amount'])

        # 2. Stripe: charge the SERVER-computed subtotal (converted to cents).
        #    Run outside the DB transaction so a slow Stripe call never holds locks.
        amount_in_cents = int((subtotal * 100).quantize(Decimal('1'), rounding=ROUND_HALF_UP))
        intent = stripe.PaymentIntent.create(
            amount=amount_in_cents,
            currency=stripe_currency,
            automatic_payment_methods={'enabled': True},
            receipt_email=data.get('email'),
            metadata={'customer_email': data.get('email'), 'currency': raw_currency,
                      'order_id': order.id},
        )
        order.stripe_payment_intent_id = intent.id
        order.save(update_fields=['stripe_payment_intent_id'])

        return Response({
            'client_secret': intent.client_secret,
            'order_id': order.id
        }, status=status.HTTP_201_CREATED)

    except _CheckoutError as e:
        return Response({'error': e.message}, status=e.status_code)
    except Exception as e:
        # Log only the error class — never the message, which can contain secrets.
        print("Backend Checkout Error:", type(e).__name__)
        return Response(
            {'error': 'Something went wrong processing your checkout on the server.'},
            status=status.HTTP_400_BAD_REQUEST
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
    except Exception as e:
        # Log only the error class — never the message (can contain secrets/PII).
        print("Registration Error:", type(e).__name__)
        return Response({'error': 'Failed to create user.'}, status=status.HTTP_400_BAD_REQUEST)


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
    # Fetch only the orders that belong to the currently logged-in user, newest first
    orders = Order.objects.filter(user=request.user).order_by('-id')
    
    # Serialize the data (which now includes your full product details!)
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


@api_view(['POST'])
@permission_classes([AllowAny])
def stripe_webhook(request):
    """
    Stripe webhook: final source of truth for card payments.

    SECURITY: signature verification is MANDATORY. If STRIPE_WEBHOOK_SECRET is
    not configured we refuse the request rather than accepting an unsigned JSON
    payload (which would let anyone forge `payment_intent.succeeded` and mark
    orders as paid for free).
    """
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE', '')
    webhook_secret = os.environ.get('STRIPE_WEBHOOK_SECRET', '')
    if not webhook_secret:
        return Response({'error': 'Webhook secret not configured.'},
                        status=status.HTTP_503_SERVICE_UNAVAILABLE)
    try:
        event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
    except Exception:
        return Response({'error': 'Invalid webhook signature.'}, status=status.HTTP_400_BAD_REQUEST)

    event_type = event.get('type', '')
    obj = (event.get('data') or {}).get('object') or {}
    intent_id = obj.get('id')
    if not intent_id:
        return Response({'received': True})

    try:
        order = Order.objects.get(stripe_payment_intent_id=intent_id)
    except Order.DoesNotExist:
        return Response({'received': True})

    if event_type == 'payment_intent.succeeded':
        # Idempotent + concurrency-safe: only the caller that claims the unpaid
        # order consumes stock, so webhook retries / races with confirm_checkout
        # can never double-decrement inventory.
        _mark_paid_and_reserve(order)
    return Response({'received': True})
