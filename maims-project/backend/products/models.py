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
    slug = models.SlugField()
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
    slug = models.SlugField()
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
    slug = models.SlugField()
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
        prices = getattr(self, '_prefetched_prices_cache', None)
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
    created_at = models.DateTimeField(auto_now_add=True)

    # --- Fulfilment workflow (managed in Admin → Orders) ---
    STATUS_CHOICES = [
        ('new', 'New - not packed yet'),
        ('packed', 'Packed'),
        ('shipped', 'Shipped'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
        ('returned', 'Returned / refunded'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='new', db_index=True)
    tracking_number = models.CharField(max_length=120, blank=True, null=True,
                                       help_text="Courier / tracking reference, e.g. 1234567890")
    admin_note = models.TextField(blank=True, null=True,
                                  help_text="Internal only - never shown to the customer")

    class Meta:
        ordering = ('-created_at',)
        verbose_name = 'Order'
        verbose_name_plural = 'Orders'
        indexes = [models.Index(fields=['-created_at'])]

    def __str__(self):
        return f"Order {self.id} - {self.first_name} {self.last_name}"

    def get_absolute_url(self):
        from django.urls import reverse
        return reverse('admin:products_order_change', args=[self.pk])

    @property
    def is_open(self):
        """True while the order still needs work (not finished or cancelled)."""
        return self.status not in ('delivered', 'cancelled', 'returned')


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