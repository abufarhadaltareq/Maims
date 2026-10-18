from decimal import Decimal

from django.core.validators import MaxValueValidator, MinValueValidator
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
    badge_text = models.CharField(max_length=100, blank=True, null=True, default='New season drop',
                                   help_text='Small pill shown above the title')
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


class HeroBannerSettings(models.Model):
    """Singleton: global controls for the homepage hero banner.

    A dedicated model (rather than env vars) so the shop can toggle the
    banner, pick its look and tune its transparency from the admin — no
    code change, no redeploy. There is exactly one row (pk=1); `HeroSlide`
    rows are the *content* (the images and copy), this row is the *stage*
    (whether the stage is open and how it looks).
    """

    # --- Show / hide ---------------------------------------------------------
    hero_enabled = models.BooleanField(
        default=True,
        verbose_name="Hero banner enabled",
        help_text="Untick to hide the entire homepage banner — the page then starts at the category strip.",
    )

    # --- Layout --------------------------------------------------------------
    HEIGHT_CHOICES = [
        ('medium', 'Medium (70-90vh)'),
        ('tall', 'Tall (85-100vh)'),
        ('full', 'Full screen'),
    ]
    height_preset = models.CharField(
        max_length=10, choices=HEIGHT_CHOICES, default='tall',
        help_text="How much of the viewport the banner fills.",
    )
    overlay_strength = models.PositiveIntegerField(
        default=45, validators=[MinValueValidator(0), MaxValueValidator(95)],
        help_text="Dark overlay over the slide image, 0-95. Higher = more readable text, less of the photo.",
    )
    kenburns_intensity = models.PositiveIntegerField(
        default=12, validators=[MinValueValidator(0), MaxValueValidator(40)],
        help_text="How much each slide zooms in during its rotation, 0-40. 0 = still, 40 = dramatic.",
    )

    # --- Transparency --------------------------------------------------------
    # The 3D background (wireframe + drifting orbs) is decorative. It can be
    # dimmed or switched off entirely, and its opacity is a separate slider
    # so the shop can keep the animation without it fighting the image.
    hero_3d_enabled = models.BooleanField(
        default=True,
        verbose_name="Show 3D background",
        help_text="The animated wireframe + drifting orbs behind the slides.",
    )
    hero_3d_opacity = models.PositiveIntegerField(
        default=45, validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Opacity of the 3D layer, 0-100. 0 hides it while keeping it enabled.",
    )
    hero_3d_blend = models.BooleanField(
        default=True,
        verbose_name="Screen blend mode",
        help_text="mix-blend-screen makes the 3D layer sit on top of the photo instead of covering it.",
    )

    # --- Motion --------------------------------------------------------------
    rotation_seconds = models.PositiveIntegerField(
        default=5, validators=[MinValueValidator(2), MaxValueValidator(30)],
        help_text="Seconds between slides. Lower = faster rotation.",
    )
    transition_ms = models.PositiveIntegerField(
        default=1100, validators=[MinValueValidator(300), MaxValueValidator(3000)],
        help_text="Crossfade duration between slides, in milliseconds.",
    )
    autoplay = models.BooleanField(
        default=True,
        verbose_name="Autoplay rotation",
        help_text="Untick to stop the slides from rotating — useful when the banner holds a single announcement.",
    )

    # --- Design tokens -------------------------------------------------------
    # These re-skin the banner without touching the stylesheet.
    accent_color = models.CharField(
        max_length=7, default='#0ea5e9',
        help_text="Highlight colour used by the badge, progress bars and buttons. Hex, e.g. #0ea5e9.",
    )
    text_shadow = models.BooleanField(
        default=True,
        verbose_name="Text drop shadow",
        help_text="A soft shadow keeps the headline readable over any photo.",
    )
    glass_cards = models.BooleanField(
        default=True,
        verbose_name="Glassmorphism card",
        help_text="The headline sits in a semi-transparent card with a blur.",
    )

    updated_at = models.DateTimeField(auto_now=True, verbose_name="Last changed")

    class Meta:
        verbose_name = 'Hero banner settings'
        verbose_name_plural = 'Hero banner settings'

    def __str__(self):
        return 'Hero banner settings'

    @classmethod
    def get(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


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
    # Deshi-besh style browsing: bust sizes (32–50), garment lengths (e.g.
    # Anarkali 53/54/56) and colour swatches. All three are comma-separated so
    # the shop can type "36,38,40" or "Red,#7A1F1F,Emerald" with no extra setup.
    # The public /facets/ endpoint collects the distinct values for the sidebar.
    color_options = models.CharField(max_length=500, blank=True, null=True,
        help_text='Comma-separated colours: names or hex swatches, e.g. Red,Emerald,#7A1F1F')
    length_options = models.CharField(max_length=250, blank=True, null=True,
        help_text='Comma-separated lengths, e.g. 53,54,56 or S,M,L')
    image = models.ImageField(upload_to='uploads/', blank=True, null=True)
    thumbnail = models.ImageField(upload_to='uploads/', blank=True, null=True)
    # --- Facebook Page sync ------------------------------------------------
    # Graph API post id ("{page_id}_{post_id}") — the idempotent key
    # that ties this record to the Facebook post it came from. NULL
    # for products entered by hand, so the unique index never collides
    # (PostgreSQL treats NULLs as distinct).
    facebook_post_id = models.CharField(max_length=64, blank=True, null=True,
                                        unique=True,
                                        help_text="Graph API post id this product was synced from")
    # Re-hosted photo (Cloudinary) when the sync pipeline uploads the
    # Facebook image to cloud storage. Preferred over the local file
    # because Meta's lookaside image URLs expire.
    facebook_image_url = models.URLField(blank=True, null=True,
                                         help_text="Cloud-hosted image URL from Facebook sync")
    # Approval gate for Facebook-synced posts: when the shop holds syncs for
    # review, new products land here hidden and are invisible to the storefront
    # until an admin approves them.
    is_visible = models.BooleanField(default=True, db_index=True,
        help_text="Untick to hide this product from the storefront without deleting it.")
    date_added = models.DateTimeField(auto_now_add=True)


    class Meta:
        ordering = ('-date_added',)
        
    def __str__(self):
        return self.name

    def get_image(self):
        # A cloud-hosted copy (Facebook sync) outlives Meta's
        # expiring lookaside URLs, so it wins when present.
        if self.facebook_image_url:
            return self.facebook_image_url
        if self.image:
            return self.image.url
        return ''

    def get_thumbnail(self):
        if self.facebook_image_url:
            return self.facebook_image_url
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

    def _split_options(self, raw):
        if not raw:
            return []
        seen = set()
        out = []
        for part in str(raw).split(','):
            val = part.strip()
            if val and val.lower() not in seen:
                seen.add(val.lower())
                out.append(val)
        return out

    def get_color_options(self):
        return self._split_options(self.color_options)

    def get_length_options(self):
        return self._split_options(self.length_options)

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
    # --- Brand identity -------------------------------------------------------
    # Uploaded logo (PNG/JPG) shown in the header/footer instead of the default
    # 'M' monogram. Blank = keep the monogram. Validated below (type + 2MB cap)
    # so a wrong upload fails with a message, not a broken header.
    # --- Top header ticker + branding (Admin → Site settings → Brand & header) ----
    # One-line messages that scroll across the top bar (marquee). Put each
    # message on its own line, e.g.
    #   Free EU shipping over €40
    #   New drop every Friday
    #   Easy 14-day returns
    # Blank = the header ticker hides itself.
    announcement_enabled = models.BooleanField(default=True,
        help_text="Show the scrolling message bar above the header.")
    announcement_messages = models.TextField(blank=True, null=True,
        default="Free EU shipping on orders over €40",
        help_text="One message per line. They scroll one after another in the top bar.")
    announcement_speed = models.PositiveIntegerField(default=30,
        help_text="Scroll speed in seconds per loop (10 = fast, 60 = slow).")
    # Short line under the logo (header + footer wordmark). Blank hides it.
    tagline = models.CharField(max_length=120, blank=True, null=True, default="Premium Fashion",
        help_text="Short line under the logo, e.g. Premium Fashion.")
    # Short footer paragraph + bottom legal line. Both fall back to defaults.
    footer_about = models.CharField(max_length=255, blank=True, null=True,
        default="Curated premium fashion, delivered worldwide.",
        help_text="One-line shop description in the footer.")
    footer_bottom_note = models.CharField(max_length=255, blank=True, null=True,
        default="Premium fashion, delivered worldwide",
        help_text="Small line at the very bottom of the footer.")
    store_name = models.CharField(max_length=120, default='Maims')
    # --- Brand color & content color (Admin → Site settings → Brand) ---
    brand_color = models.CharField(max_length=7, default='#7C3AED',
        help_text="Main brand color (purple gradient uses this).")
    content_color = models.CharField(max_length=7, default='#1F2937',
        help_text="Main content text color (headings, body text).")
    content_text_secondary = models.CharField(max_length=7, default='#4B5563',
        help_text="Secondary content text color (descriptions, labels).")
    heading_color = models.CharField(max_length=7, default='#7C3AED',
        help_text="Heading text color (page titles, section headers).")
    logo = models.ImageField(upload_to='uploads/brand/', blank=True, null=True,
                             help_text="PNG or JPG, max 2MB. Shown in the header and footer.")
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
    # Cash on Delivery was retired: the three methods below are all a storefront
    # can offer now (card via Stripe, PayPal, or a WhatsApp-confirmed order).
    stripe_enabled = models.BooleanField(default=True)
    paypal_enabled = models.BooleanField(default=True, verbose_name="PayPal enabled")
    updated_at = models.DateTimeField(auto_now=True)

    # --- Only PNG/JPG brand logos, max 2MB. The check lives here (not only in the
    # form) so API/admin/shell uploads are all guarded the same way.
    LOGO_MAX_BYTES = 2 * 1024 * 1024
    LOGO_ALLOWED_TYPES = ('image/png', 'image/jpeg')
    LOGO_ALLOWED_EXTS = ('.png', '.jpg', '.jpeg')

    def clean(self):
        super().clean()
        logo = self.logo
        if not logo:
            return
        from django.core.exceptions import ValidationError
        import os
        content_type = getattr(logo.file, 'content_type', '') if hasattr(logo, 'file') else ''
        ext = os.path.splitext(logo.name or '')[1].lower()
        if (content_type and content_type not in self.LOGO_ALLOWED_TYPES) or \
                (ext and ext not in self.LOGO_ALLOWED_EXTS):
            raise ValidationError({'logo': 'Please upload a PNG or JPG image.'})
        size = getattr(logo.file, 'size', None) if hasattr(logo, 'file') else None
        if size and size > self.LOGO_MAX_BYTES:
            raise ValidationError({'logo': 'Logo must be 2MB or smaller.'})

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
    whatsapp_business_account_id = models.CharField(max_length=64, blank=True, null=True,
        help_text="WhatsApp Business Account ID (WABA ID) from Meta Business Manager > Business Info")
    whatsapp_webhook_secret = models.CharField(max_length=128, blank=True, null=True,
        help_text="Secret used to verify WhatsApp webhook signatures (X-Hub-Signature-256)")

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
    facebook_app_id = models.CharField(max_length=64, blank=True, null=True,
        help_text="Meta App ID from developers.facebook.com — overrides FACEBOOK_APP_ID when set")
    facebook_app_secret = models.CharField(max_length=128, blank=True, null=True,
        help_text="Meta App Secret, used to verify webhook signatures — overrides FACEBOOK_APP_SECRET when set")
    facebook_webhook_verify_token = models.CharField(max_length=128, blank=True, null=True,
        help_text="Token Meta sends when verifying the feed webhook — overrides FACEBOOK_WEBHOOK_VERIFY_TOKEN when set")
    facebook_sync_interval_minutes = models.PositiveIntegerField(default=60,
        help_text="How often the background catalogue sync should run (minutes). 0 disables scheduled syncs.")
    facebook_auto_approve_sync = models.BooleanField(default=True,
        help_text="Publish Facebook-synced products to the storefront immediately. "
                  "Untick to hold new syncs for review: they stay hidden until an admin approves them.")

    # --- Store email / SMTP (admin-controlled, overrides the .env values) -------------------
    email_from_address = models.EmailField(blank=True, null=True,
        help_text="Sender address on order emails. Falls back to DEFAULT_FROM_EMAIL when blank.")
    smtp_host = models.CharField(max_length=255, blank=True, null=True,
        help_text="SMTP server for order emails (e.g. smtp.gmail.com). Blank = use the Django email backend.")
    smtp_port = models.PositiveIntegerField(default=587,
        help_text="SMTP port (587 for STARTTLS, 465 for SSL-implicit).")
    smtp_use_tls = models.BooleanField(default=True,
        help_text="Use STARTTLS when talking to the SMTP server.")
    smtp_username = models.CharField(max_length=255, blank=True, null=True,
        help_text="SMTP login (usually the same address as the sender).")
    smtp_password = models.CharField(max_length=255, blank=True, null=True,
        help_text="SMTP password or app-specific password.")
    receipt_footer_text = models.TextField(blank=True, null=True,
        help_text="Optional custom text appended to every order receipt (returns policy, shop hours, …).")

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

    def clean(self):
        super().clean()
        logo = self.logo
        if not logo:
            return
        from django.core.exceptions import ValidationError
        import os
        content_type = getattr(logo.file, 'content_type', '') if hasattr(logo, 'file') else ''
        ext = os.path.splitext(logo.name or '')[1].lower()
        if (content_type and content_type not in self.LOGO_ALLOWED_TYPES) or \
                (ext and ext not in self.LOGO_ALLOWED_EXTS):
            raise ValidationError({'logo': 'Please upload a PNG or JPG image.'})
        size = getattr(logo.file, 'size', None) if hasattr(logo, 'file') else None
        if size and size > self.LOGO_MAX_BYTES:
            raise ValidationError({'logo': 'Logo must be 2MB or smaller.'})


# --- EMAIL MARKETING OPT-IN (singleton, editable in Admin) ---

class CustomerNotificationSettings(models.Model):
    """One row controlling how shoppers may be added to the mailing list.

    Nothing here sends email by itself — it gates the two places a shopper can
    join the list (footer sign-up form and the checkout opt-in checkbox), and
    records which consent strategy the shop follows so the wording on those
    forms can match. GDPR/PECR: consent must be freely given, so the checkout
    box starts unticked unless the shop deliberately chooses an opt-out
    strategy for a region where that is lawful.
    """
    OPT_IN_STRATEGIES = [
        # The checkbox ships unticked; no means no.
        ('explicit', 'Explicit opt-in (box starts unticked)'),
        # Pre-ticked boxes are not valid consent in the EU/UK, so this exists
        # only for regions where opt-out is lawful and is NOT the default.
        ('opt_out', 'Opt-out (box starts ticked)'),
    ]

    # Storefront footer sign-up form: hide it entirely when the shop is not
    # ready to receive subscribers (e.g. no sender configured yet).
    signup_enabled = models.BooleanField(default=True,
        help_text="Show the email sign-up form in the storefront footer")
    # Checkout checkbox: capture the address with the order too.
    checkout_opt_in_enabled = models.BooleanField(default=True,
        help_text="Show the marketing opt-in checkbox during checkout")
    # Consent strategy described above — drives the default state of both forms.
    opt_in_strategy = models.CharField(max_length=16, choices=OPT_IN_STRATEGIES, default='explicit',
        help_text="'Explicit' keeps the checkout box unticked until the shopper ticks it")
    # Consent text shown next to the checkout checkbox; kept editable so legal
    # wording can be tightened without a deploy.
    consent_text = models.CharField(max_length=255, default=(
        "Email me about new drops, restocks and offers. Unsubscribe any time."
    ))
    # Where captured addresses are delivered when a send is triggered.
    recipient_email = models.EmailField(blank=True, null=True,
        help_text="Mailbox that receives captured sign-ups; leave empty to stop collecting")
    # Quick status an operator can see on the changelist without opening the row.
    status = models.CharField(max_length=12, default='active',
        choices=[('active', 'Collecting'), ('paused', 'Paused')],
        help_text="'Paused' stops both forms from accepting new addresses")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Customer notification settings'
        verbose_name_plural = 'Customer notification settings'

    def __str__(self):
        return 'Customer notification settings'

    @classmethod
    def get(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    @property
    def accepts_signups(self):
        """True when at least one storefront form may capture an address."""
        return self.status == 'active' and bool(self.recipient_email)

    @property
    def checkout_box_starts_ticked(self):
        """The checkout checkbox default; only 'opt-out' regions pre-tick it."""
        return self.opt_in_strategy == 'opt_out'


# --- CHECKOUT & ORDER HANDLING ---

class Order(models.Model):
    PAYMENT_METHODS = [
        ('stripe', 'Card (Stripe)'),
        ('paypal', 'PayPal'),
        ('whatsapp', 'WhatsApp order'),
    ]
    CURRENCY_CHOICES = [
        ('EUR', 'Euro (€)'),
        ('USD', 'US Dollar ($)'),
        ('SEK', 'Swedish Krona (kr)'),
        ('BDT', 'Bangladeshi Taka (৳)'),
        ('PKR', 'Pakistani Rupee (Rs)'),
    ]
    user = models.ForeignKey(User, related_name='orders', on_delete=models.SET_NULL, blank=True, null=True)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField()
    # Required: the confirmation email, WhatsApp updates and the courier all
    # need a phone number, so checkout rejects an order without one.
    phone = models.CharField(max_length=20, default='')
    address = models.CharField(max_length=255)
    zipcode = models.CharField(max_length=20)
    place = models.CharField(max_length=100)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, choices=CURRENCY_CHOICES, default='EUR')
    # How the customer is paying: card via Stripe, PayPal, or a WhatsApp order
    # (confirmed by the shop on chat). Cash on Delivery was removed — the
    # storefront never offers it, and orders that predate the change still carry
    # their stored value for historical display.
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS, default='stripe')
    # Stripe PaymentIntent id — the handle for webhooks, refunds and receipts.
    # Blank for WhatsApp orders, which never touch Stripe.
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
    # Email-marketing consent captured at checkout, only stored when the
    # CustomerNotificationSettings-gated checkbox was shown and ticked. This is
    # the shop's proof of consent for that address.
    marketing_opt_in = models.BooleanField(default=False)
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
    def payment_method_label(self):
        """Readable label shown to customers in emails and the admin."""

        return dict(self.PAYMENT_METHODS).get(self.payment_method, self.payment_method)

    @property
    def payment_badge(self):
        """A coloured pill (foreground, background) keyed by payment method."""

        return {
            'stripe': ('#1d4ed8', '#dbeafe'),
            'paypal': ('#003087', '#e0f2fe'),
            'whatsapp': ('#15803d', '#dcfce7'),
        }.get(self.payment_method, ('#111827', '#e5e7eb'))

    @property
    def payment_status_message(self):
        """One-line text for the customer describing how the order was paid."""

        if self.payment_method == 'whatsapp':
            return 'Your order will be confirmed on WhatsApp before it is prepared.'
        return f'Your order was placed with {self.payment_method_label}.'

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
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, blank=True, null=True)
    size = models.CharField(max_length=50, blank=True, null=True)
    stitching_selected = models.CharField(max_length=50, default='unstitched')
    price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.IntegerField(default=1)
    product_name = models.CharField(max_length=255, blank=True, default='',
        help_text='Snapshot of the product name at order time, so receipts survive product cleanup.')

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
    # Retry bookkeeping: how many times this (order, channel, audience, event)
    # has already been re-attempted, so the background retry command can cap
    # itself instead of hammering a broken provider forever.
    attempts = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ('-created_at',)
        verbose_name = 'Order notification'
        verbose_name_plural = 'Order notifications'
        indexes = [
            # The dedupe lookup is always "for this order, channel and audience".
            models.Index(fields=['order', 'channel', 'audience']),
            models.Index(fields=['status', 'attempts']),
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


# --- WISHLIST ---

class WishlistItem(models.Model):
    """
    A product saved by a user for later ("wishlist" / "saved items").

    One row per (user, product) — the unique constraint below guarantees a
    double-tap on the heart can never create a duplicate row, and the DELETE
    endpoint is idempotent so removing an item twice is simply a no-op.

    This is deliberately separate from the cart: a wishlist holds intent, not a
    commitment to buy, and it survives checkout (the cart is cleared on order).
    """

    user = models.ForeignKey(User, related_name='wishlist_items', on_delete=models.CASCADE)
    product = models.ForeignKey(Product, related_name='wishlisted_by', on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ('-created_at', '-id')  # -id breaks ties within the same second
        verbose_name = 'Wishlist item'
        verbose_name_plural = 'Wishlist items'
        constraints = [
            # One row per user per product: hearting the same product twice
            # returns the existing row instead of failing.
            models.UniqueConstraint(fields=['user', 'product'], name='unique_wishlist_item_per_user_product'),
        ]
        indexes = [
            # The list endpoint is always "this user's items, newest first".
            models.Index(fields=['user', '-created_at']),
        ]

    def __str__(self):
        return f'{self.user.username} ♥ {self.product_id}'
        return 'Verified customer'
