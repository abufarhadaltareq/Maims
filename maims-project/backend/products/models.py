from decimal import Decimal

from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

# --- CATEGORY & CATALOG MANAGEMENT ---

# Stock at or below this is flagged as "needs restocking" in the admin. Not a
# hard rule: the storefront keeps selling until the number reaches zero.
RESTOCK_LEVEL = 3


class Category(models.Model):
    name = models.CharField(max_length=255)
    # Unique: the public API resolves products with `.get(slug=...)`, so a duplicate
    # slug turns a single product page into a 500.
    slug = models.SlugField(unique=True)
    # Enables infinite-depth parent/child categories (e.g., Women -> Clothing -> Unstitched)
    parent = models.ForeignKey('self', related_name='children', on_delete=models.CASCADE, blank=True, null=True)
    # Showcase card image for the "Shop by Category" homepage section
    image = models.ImageField(upload_to='uploads/categories/', blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    # Show this category on the homepage "Shop by Category" strip
    show_on_homepage = models.BooleanField(default=True)
    homepage_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ('homepage_order', 'name',)
        verbose_name_plural = 'Categories'

    def __str__(self):
        if self.parent:
            return f"{self.parent.name} >> {self.name}"
        return self.name

    def get_image(self):
        if self.image:
            return self.image.url
        return ''


class HeroSlide(models.Model):
    """Homepage hero banner slides, fully editable from Django Admin."""
    title = models.CharField(max_length=255, default='Elevate Your Everyday Style')
    subtitle = models.TextField(blank=True, null=True, default="Discover curated premium clothing collections tailored just for you.")
    button_text = models.CharField(max_length=100, blank=True, null=True, default='Shop Latest Drop')
    # Where the button goes: internal path (/category/women) or full URL
    button_link = models.CharField(max_length=500, blank=True, null=True, default='#latest-products',
                                   help_text="Internal path like /category/women-clothing or #latest-products, or full https:// URL")
    image = models.ImageField(upload_to='uploads/hero/', blank=True, null=True)
    external_image_url = models.URLField(blank=True, null=True,
                                         help_text="Optional: paste an https:// image URL instead of uploading")
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ('order', 'id',)

    def __str__(self):
        state = 'active' if self.is_active else 'hidden'
        return f"Hero #{self.order} - {self.title[:40]} ({state})"

    def get_image_url(self):
        if self.image:
            return self.image.url
        return self.external_image_url or ''


class Collection(models.Model):
    # Group items by seasonal catalogs (e.g., "Festive Eid Collection", "Summer '26 Basics")
    name = models.CharField(max_length=255)
    # Unique: the public API resolves products with `.get(slug=...)`, so a duplicate
    # slug turns a single product page into a 500.
    slug = models.SlugField(unique=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ('name',)

    def __str__(self):
        return self.name


# --- PRODUCT CONFIGURATION ---

class Product(models.Model):
    STITCHING_CHOICES = [
        ('unstitched', 'Unstitched'),
        ('ready_to_wear', 'Ready to Wear'),
        ('both', 'Available in Both'),
    ]

    FABRIC_CHOICES = [
        ('lawn', 'Lawn'),
        ('silk', 'Silk'),
        ('organza', 'Organza'),
        ('velvet', 'Velvet'),
        ('cotton', 'Cotton'),
        ('chiffon', 'Chiffon'),
        ('other', 'Other Fabric'),
    ]

    category = models.ForeignKey(Category, related_name='products', on_delete=models.CASCADE)
    collection = models.ForeignKey(Collection, related_name='products', on_delete=models.SET_NULL, blank=True, null=True)
    name = models.CharField(max_length=255)
    # Unique: the public API resolves products with `.get(slug=...)`, so a duplicate
    # slug turns a single product page into a 500.
    slug = models.SlugField(unique=True)
    brand_name = models.CharField(max_length=100, blank=True, null=True, help_text="e.g., Sana Safinaz, Maria.B (Label used for frontend brand filtering)")
    description = models.TextField(blank=True, null=True)
    
    # 🌟 OPTIONAL METADATA FIELDS: Left blank for non-clothing inventory like bags/jewelry
    fabric_type = models.CharField(max_length=50, choices=FABRIC_CHOICES, blank=True, null=True)
    stitching_type = models.CharField(max_length=50, choices=STITCHING_CHOICES, blank=True, null=True)
    material_type = models.CharField(max_length=100, blank=True, null=True, help_text="For jewelry/bags, e.g., 'Gold Plated', 'Genuine Leather'")
    
    stock = models.IntegerField(default=0)
    size_options = models.CharField(max_length=250, blank=True, null=True, help_text='Comma-separated options like S,M,L or One Size')
    image = models.ImageField(upload_to='uploads/', blank=True, null=True)
    thumbnail = models.ImageField(upload_to='uploads/', blank=True, null=True)
    date_added = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ('-date_added',)
        
    def __str__(self):
        return self.name

    def get_image(self):
        if self.image:
            return self.image.url
        return ''

    def get_thumbnail(self):
        if self.thumbnail:
            return self.thumbnail.url
        else:
            if self.image:
                return self.image.url
            return ''

    def get_size_options(self):
        if not self.size_options:
            return []
        return [size.strip() for size in self.size_options.split(',') if size.strip()]

    @property
    def is_in_stock(self):
        return (self.stock or 0) > 0

    def get_price(self, currency='EUR'):
        """Return Decimal price for a currency, falling back to first available price."""
        currency = (currency or 'EUR').upper()
        prices = self._cached_prices()
        if prices is not None:
            for p in prices:
                if p.currency == currency:
                    return p.price
            if len(prices) > 0:
                return prices[0].price
            return None
        exact = self.prices.filter(currency=currency).first()
        if exact:
            return exact.price
        first = self.prices.first()
        return first.price if first else None

    def _cached_prices(self):
        """
        Return the prefetched CurrencyPrice list, or None when nothing is cached.

        Django exposes prefetch results through ``_prefetched_objects_cache``, keyed
        by the related accessor name. Reading ``_prefetched_prices_cache`` instead —
        as this method used to — always missed, so every product paid for a fresh
        prices query no matter how carefully the queryset had been optimised.
        That turned a 200-product listing into 200 extra round trips.
        """
        cache = getattr(self, '_prefetched_objects_cache', None)
        if cache is not None:
            return cache.get('prices')
        return None

    def get_price_exact(self, currency='EUR'):
        """
        Return the Decimal price defined for EXACTLY this currency, else None.

        Checkout MUST use this instead of `get_price()`. The display-oriented
        fallback inside `get_price()` returns *some* other currency's number when
        the requested currency has no stored price — which would let a customer
        request a low-value currency (e.g. BDT) while the store only defines a
        high-value one (e.g. EUR), and be charged the foreign number untranslated.
        Returning None here forces the caller to reject such orders.
        """
        currency = (currency or 'EUR').upper()
        # `self.prices.all()` reuses the prefetch_related('prices') cache when present.
        for cp in self.prices.all():
            if cp.currency == currency:
                return cp.price
        return None


    @property
    def average_rating(self):
        """Mean star rating across approved reviews, or None when there are none.

        The queryset annotations used by the catalogue endpoints
        (`rating_average` / `rating_count`) take priority and avoid this query;
        this property is the correct-but-slower fallback for a single product.
        """
        from django.db.models import Avg

        return self.reviews.filter(is_approved=True).aggregate(a=Avg('rating'))['a']

    @property
    def review_count(self):
        return self.reviews.filter(is_approved=True).count()


class ProductMedia(models.Model):
    MEDIA_TYPES = [
        ('image', 'Image'),
        ('video', 'Video'),
    ]
    product = models.ForeignKey(Product, related_name='media', on_delete=models.CASCADE)
    media_type = models.CharField(max_length=10, choices=MEDIA_TYPES, default='image')
    title = models.CharField(max_length=150, blank=True)
    file = models.FileField(upload_to='uploads/', blank=True, null=True)
    external_url = models.URLField(blank=True, null=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order']
        verbose_name = 'Product media'
        verbose_name_plural = 'Product media'

    def __str__(self):
        return f"{self.product.name} media #{self.order}"

    def get_url(self):
        if self.file:
            return self.file.url
        return self.external_url or ''


# 🌟 MULTI-CURRENCY CONFIGURATION
class CurrencyPrice(models.Model):
    CURRENCY_CHOICES = [
        ('USD', 'US Dollar ($)'),
        ('EUR', 'Euro (€)'),
        ('SEK', 'Swedish Krona (kr)'),
        ('BDT', 'Bangladeshi Taka (৳)'),
        ('PKR', 'Pakistani Rupee (Rs)'),
    ]
    
    product = models.ForeignKey(Product, related_name='prices', on_delete=models.CASCADE)
    currency = models.CharField(max_length=3, choices=CURRENCY_CHOICES)
    price = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        unique_together = ('product', 'currency')

    def __str__(self):
        return f"{self.currency} {self.price}"


# --- SITE / SOCIAL / PAYMENT SETTINGS (singleton, editable in Admin) ---

class SiteSettings(models.Model):
    """Single row controlling storefront links + payment toggles. Admin edits this; frontend reads it."""
    facebook_page_url = models.URLField(blank=True, null=True,
        help_text="e.g. https://www.facebook.com/yourshop")
    facebook_shop_url = models.URLField(blank=True, null=True,
        help_text="Optional: link to your Facebook Shop tab")
    # --- Extra social links (optional; blank ones simply won't render on the storefront) ---
    instagram_url = models.URLField(blank=True, null=True,
        help_text="e.g. https://www.instagram.com/yourshop")
    tiktok_url = models.URLField(blank=True, null=True,
        help_text="e.g. https://www.tiktok.com/@yourshop")
    twitter_url = models.URLField(blank=True, null=True, verbose_name="X (Twitter) URL",
        help_text="e.g. https://x.com/yourshop")
    youtube_url = models.URLField(blank=True, null=True,
        help_text="e.g. https://www.youtube.com/@yourshop")
    linkedin_url = models.URLField(blank=True, null=True,
        help_text="e.g. https://www.linkedin.com/company/yourshop")
    # WhatsApp Business number in international format WITHOUT '+' — e.g. 351912345678
    whatsapp_number = models.CharField(max_length=20, blank=True, null=True,
        help_text="WhatsApp Business number, digits only with country code, e.g. 351912345678")
    whatsapp_enabled = models.BooleanField(default=True)
    whatsapp_greeting = models.CharField(max_length=255, blank=True, null=True, default="Hello Maims! I want to order:",
        help_text="Prefill text before the cart details in the WhatsApp message")
    cod_enabled = models.BooleanField(default=True, verbose_name="Cash on Delivery enabled")
    stripe_enabled = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    # --- Outbound notifications -------------------------------------------------
    # Everything below is configured here (not in env vars) so the shop can be set
    # up from the admin. Any blank value disables that channel: a notifier that is
    # not configured logs a 'skipped' row and moves on, it never raises.

    # Who receives the "new order" alert.
    notification_email = models.EmailField(blank=True, null=True,
        help_text="Address that receives a new-order alert. Falls back to ADMIN_RECEIVER_EMAIL.")
    admin_whatsapp_number = models.CharField(max_length=20, blank=True, null=True,
        help_text="Digits with country code, e.g. 351912345678 — receives the new-order alert on WhatsApp")
    # Tell the customer about their own order automatically (confirmation + every
    # status change up to delivery).
    customer_notifications_enabled = models.BooleanField(default=True,
        help_text="Email each customer when their order status changes")
    customer_whatsapp_notifications = models.BooleanField(default=True,
        help_text="Also send those updates over WhatsApp, for customers who opted in at checkout")

    # --- WhatsApp Business Cloud API (Meta) -------------------------------------
    whatsapp_api_token = models.CharField(max_length=255, blank=True, null=True,
        help_text="Permanent/system-user token from Meta for WhatsApp Cloud API")
    whatsapp_phone_number_id = models.CharField(max_length=64, blank=True, null=True,
        help_text="Phone Number ID from WhatsApp > API Setup (not the phone number itself)")

    # --- Facebook page posting ---------------------------------------------------
    facebook_page_id = models.CharField(max_length=64, blank=True, null=True,
        help_text="Numeric Page ID — not the page name or URL")
    facebook_page_access_token = models.CharField(max_length=512, blank=True, null=True,
        help_text="Page access token with pages_manage_posts permission")
    facebook_post_on_delivery = models.BooleanField(default=True,
        help_text="Publish a \"success story\" to the Facebook page when an order is delivered")
    facebook_success_story_template = models.TextField(blank=True, null=True, default=(
        "Just shipped {product_names} to {place}! Thank you {first_name} for choosing Maims."
    ), help_text="Placeholders: {order_id}, {first_name}, {place}, {product_names}, {currency}, {total}")

    class Meta:
        verbose_name = 'Site settings'
        verbose_name_plural = 'Site settings'

    def __str__(self):
        return 'Site settings'

    @classmethod
    def get(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    def whatsapp_link(self, message=''):
        import urllib.parse
        if not self.whatsapp_number:
            return ''
        num = ''.join(ch for ch in self.whatsapp_number if ch.isdigit())
        if not num:
            return ''
        return f"https://wa.me/{num}?text={urllib.parse.quote(message or self.whatsapp_greeting or '')}"


# --- CHECKOUT & ORDER HANDLING ---

class Order(models.Model):
    PAYMENT_METHODS = [
        ('stripe', 'Stripe (card)'),
        ('cod', 'Cash on Delivery'),
        ('whatsapp', 'WhatsApp order'),
    ]
    PAYMENT_STATUSES = [
        ('EUR', 'Euro (€)'),
        ('USD', 'US Dollar ($)'),
        ('SEK', 'Swedish Krona (kr)'),
        ('BDT', 'Bangladeshi Taka (৳)'),
        ('PKR', 'Pakistani Rupee (Rs)'),
    ]
    CURRENCY_CHOICES = PAYMENT_STATUSES
    user = models.ForeignKey(User, related_name='orders', on_delete=models.SET_NULL, blank=True, null=True)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=20, blank=True, null=True)
    address = models.CharField(max_length=255)
    zipcode = models.CharField(max_length=20)
    place = models.CharField(max_length=100)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, choices=CURRENCY_CHOICES, default='EUR')
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS, default='stripe')
    stripe_payment_intent_id = models.CharField(max_length=255, blank=True, null=True)
    is_paid = models.BooleanField(default=False)
    # Client-supplied dedupe key (the `Idempotency-Key` request header). A retried
    # checkout POST — double-clicked button, flaky mobile network, refresh mid
    # redirect — must not create a second order or reserve the stock twice.
    # NULL for orders placed before this existed and for API clients that send no
    # header; Postgres/MySQL both allow many NULLs under a unique index.
    checkout_key = models.CharField(max_length=64, blank=True, null=True, unique=True)
    # Guards the reverse operation: refund/cancel puts stock back exactly once,
    # no matter how many times the webhook is retried.
    stock_released = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    # --- Fulfilment workflow (managed in Admin → Orders) ---
    # 'new' and 'accepted' are distinct on purpose: staff must confirm the shop
    # can actually fulfil an order before packing starts, and the customer is
    # told which of those happened.
    STATUS_CHOICES = [
        ('new', 'New - awaiting shop decision'),
        ('accepted', 'Accepted - confirmed by the shop'),
        ('rejected', 'Not taken - declined by the shop'),
        ('packed', 'Packed'),
        ('shipped', 'Shipped'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
        ('returned', 'Returned / refunded'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='new', db_index=True)
    # Shown to the customer in the rejection email/WhatsApp message.
    rejection_reason = models.CharField(max_length=255, blank=True, null=True,
        help_text="Shown to the customer when the shop declines the order")
    # Whether the customer asked to receive order updates over WhatsApp. WhatsApp
    # only permits business-initiated messages to people who opted in, so this flag
    # is collected at checkout and enforced again at send time.
    whatsapp_opt_in = models.BooleanField(default=False)
    # The status the customer has already been told about. Guarantees exactly one
    # notification per transition even if an order is saved several times (the admin
    # changelist saves the whole form, actions save again, and a retry may re-save).
    last_notified_status = models.CharField(max_length=20, blank=True, default='')
    tracking_number = models.CharField(max_length=120, blank=True, null=True,
                                       help_text="Courier / tracking reference, e.g. 1234567890")
    admin_note = models.TextField(blank=True, null=True,
                                  help_text="Internal only - never shown to the customer")

    # Customer-facing labels. The STATUS_CHOICES text is written for staff
    # ("Accepted - confirmed by the shop"); these read naturally in an email
    # subject line or a WhatsApp message.
    STATUS_MESSAGE_LABELS = {
        'new': 'Order received',
        'accepted': 'Order confirmed',
        'rejected': 'Order declined',
        'packed': 'Order packed',
        'shipped': 'Order shipped',
        'delivered': 'Order delivered',
        'cancelled': 'Order cancelled',
        'returned': 'Order returned',
    }

    class Meta:
        ordering = ('-created_at',)
        verbose_name = 'Order'
        verbose_name_plural = 'Orders'
        indexes = [models.Index(fields=['-created_at'])]

    def __str__(self):
        return f"Order {self.id} - {self.first_name} {self.last_name}"

    @property
    def status_message_label(self):
        return self.STATUS_MESSAGE_LABELS.get(self.status, self.status.replace('_', ' ').title())

    def get_absolute_url(self):
        from django.urls import reverse
        return reverse('admin:products_order_change', args=[self.pk])

    @property
    def is_open(self):
        """True while the order still needs work (not finished or closed)."""
        return self.status not in ('delivered', 'cancelled', 'returned', 'rejected')

    # Statuses the customer should be told about. 'new' is included because it is
    # the order confirmation; 'rejected' and 'cancelled' are included because a
    # customer must never be left wondering why an order vanished. Everything
    # after 'delivered' is silent, per the requirement to notify until delivery.
    NOTIFY_STATUSES = ('new', 'accepted', 'rejected', 'packed', 'shipped', 'delivered', 'cancelled')

    @property
    def should_notify_customer(self):
        return self.status in self.NOTIFY_STATUSES


class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name='items', on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    size = models.CharField(max_length=50, blank=True, null=True)
    stitching_selected = models.CharField(max_length=50, default='unstitched')
    price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.IntegerField(default=1)

    class Meta:
        verbose_name = 'Order item'
        verbose_name_plural = 'Order items'

    def __str__(self):
        size_text = f" ({self.size})" if self.size else ''
        return f"{self.quantity} x {self.product.name}{size_text}"

    @property
    def line_total(self):
        """Quantity x unit price. Used by the admin order pages and packing slips."""
        return (self.price or Decimal('0')) * (self.quantity or 0)


# --- AUTOMATED PROFILES ---

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    phone = models.CharField(max_length=50, blank=True, null=True)
    address = models.CharField(max_length=255, blank=True, null=True)
    zipcode = models.CharField(max_length=50, blank=True, null=True)
    place = models.CharField(max_length=100, blank=True, null=True)

    def __str__(self):
        return f"Profile for {self.user.username}"


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    instance.profile.save()

# --- OUTBOUND NOTIFICATIONS ---

class OrderNotification(models.Model):
    """
    A durable record of every message the shop tried to send about an order.

    Three reasons this is a table rather than a log line:

    1. Staff need to answer "did the customer actually get the dispatch text?"
      without digging through container logs.
    2. It makes sending idempotent. A retried webhook or a double-clicked admin
      button re-enters the notifier; we look for an existing successful row for
      the same (order, channel, audience, event) and skip instead of messaging a
      customer twice.
    3. Failures are visible and retryable instead of vanishing into a logger.

    No send is ever allowed to raise into the caller: a customer's bank must not
    see a 500 because Meta was briefly unreachable.
    """

    CHANNELS = [
        ('email', 'Email'),
        ('whatsapp', 'WhatsApp'),
        ('facebook', 'Facebook page'),
    ]
    AUDIENCES = [
        ('customer', 'Customer'),
        ('admin', 'Shop owner'),
    ]
    STATUSES = [
        ('sent', 'Sent'),
        ('failed', 'Failed'),
        ('skipped', 'Skipped'),
    ]

    order = models.ForeignKey(Order, related_name='notifications', on_delete=models.CASCADE)
    channel = models.CharField(max_length=20, choices=CHANNELS)
    audience = models.CharField(max_length=20, choices=AUDIENCES)
    # The status (or event) this message reports: 'new', 'shipped', 'delivered', ...
    event = models.CharField(max_length=32)
    status = models.CharField(max_length=10, choices=STATUSES, db_index=True)
    recipient = models.CharField(max_length=255, blank=True, default='')
    subject = models.CharField(max_length=255, blank=True, default='')
    body = models.TextField(blank=True, default='')
    # Provider response, trimmed. Never log the access token or full API payload.
    error = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    sent_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ('-created_at',)
        verbose_name = 'Order notification'
        verbose_name_plural = 'Order notifications'
        indexes = [
            # The dedupe lookup is always "for this order, channel and audience".
            models.Index(fields=['order', 'channel', 'audience']),
        ]

    def __str__(self):
        return f"#{self.order_id} {self.channel}/{self.audience} {self.event} ({self.status})"

    @property
    def is_success(self):
        return self.status == 'sent'


# --- PRODUCT REVIEWS ---

class Review(models.Model):
    """
    A star rating plus comment on a product.

    Reviews are tied to a *purchase* rather than only an account: `order` records
    which delivered order the reviewer bought from, so the storefront can mark the
    review as verified. A logged-in customer who has never ordered can still
    review (people do), but it shows as unverified.
    """

    RATING_CHOICES = [(i, f'{i} star' + ('s' if i != 1 else '')) for i in range(1, 6)]

    product = models.ForeignKey(Product, related_name='reviews', on_delete=models.CASCADE)
    # SET_NULL so deleting an account does not delete the shop's social proof.
    user = models.ForeignKey(User, related_name='reviews', on_delete=models.SET_NULL,
                             blank=True, null=True)
    order = models.ForeignKey(Order, related_name='reviews', on_delete=models.SET_NULL,
                              blank=True, null=True,
                              help_text="Set automatically when the reviewer has a delivered order")
    rating = models.PositiveSmallIntegerField(choices=RATING_CHOICES)
    title = models.CharField(max_length=120, blank=True, default='')
    comment = models.TextField(blank=True, default='')
    # Staff can hide a review (spam, abuse) without deleting it.
    is_approved = models.BooleanField(default=True)
    # Recorded at write time because Order.items is not guaranteed to survive edits,
    # and the product name shown later may have been renamed.
    product_name_snapshot = models.CharField(max_length=255, blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ('-created_at',)
        verbose_name = 'Review'
        verbose_name_plural = 'Reviews'
        constraints = [
            # One review per customer per product. NULL users (guests are not
            # allowed, but a deleted account leaves a NULL) are exempt from the
            # conflict because SQL treats NULLs as distinct.
            models.UniqueConstraint(fields=['product', 'user'], name='unique_review_per_user_product'),
            # Defensive: a rating outside 1..5 must never reach the database even
            # if a future serializer is edited carelessly.
            models.CheckConstraint(
                condition=models.Q(rating__gte=1, rating__lte=5),
                name='review_rating_between_1_and_5',
            ),
        ]
        indexes = [models.Index(fields=['product', 'is_approved'])]

    def __str__(self):
        return f"{self.rating}* {self.product_name_snapshot or self.product_id}"

    @property
    def is_verified_purchase(self):
        return self.order_id is not None

    @property
    def reviewer_name(self):
        """First name + last initial, so reviews carry a name but not an identity."""
        if self.user_id and self.user:
            last = (self.user.last_name or '').strip()
            initial = f"{last[0].upper()}." if last else ''
            return f"{self.user.first_name or self.user.username} {initial}".strip()
        return 'Verified customer'
