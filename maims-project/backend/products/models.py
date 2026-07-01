from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save 
from django.dispatch import receiver

# --- CATEGORY & CATALOG MANAGEMENT ---

class Category(models.Model):
    name = models.CharField(max_length=255)
    slug = models.SlugField()
    # Enables infinite-depth parent/child categories (e.g., Women -> Clothing -> Unstitched)
    parent = models.ForeignKey('self', related_name='children', on_delete=models.CASCADE, blank=True, null=True)

    class Meta:
        ordering = ('name',)
        verbose_name_plural = 'Categories'
        
    def __str__(self):
        if self.parent:
            return f"{self.parent.name} >> {self.name}"
        return self.name


class Collection(models.Model):
    # Group items by seasonal catalogs (e.g., "Festive Eid Collection", "Summer '26 Basics")
    name = models.CharField(max_length=255)
    slug = models.SlugField()
    is_active = models.BooleanField(default=True)

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

    def is_in_stock(self):
        return self.stock > 0


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


# --- CHECKOUT & ORDER HANDLING ---

class Order(models.Model):
    user = models.ForeignKey(User, related_name='orders', on_delete=models.SET_NULL, blank=True, null=True)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=20, blank=True, null=True)
    address = models.CharField(max_length=255)
    zipcode = models.CharField(max_length=20)
    place = models.CharField(max_length=100)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    stripe_payment_intent_id = models.CharField(max_length=255, blank=True, null=True)
    is_paid = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Order {self.id} - {self.first_name} {self.last_name}"


class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name='items', on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    size = models.CharField(max_length=50, blank=True, null=True)
    stitching_selected = models.CharField(max_length=50, default='unstitched')
    price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.IntegerField(default=1)

    def __str__(self):
        size_text = f" ({self.size})" if self.size else ''
        return f"{self.quantity} x {self.product.name}{size_text}"


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