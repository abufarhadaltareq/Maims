from django.db import models
from django.contrib.auth.models import User # 🌟 Make sure this is imported at the top
# 🌟 Import this so a profile is automatically generated whenever a user registers!
from django.db.models.signals import post_save 
from django.dispatch import receiver

# --- YOUR ORIGINAL MODELS (Restored) ---
class Category(models.Model):
    name = models.CharField(max_length=255)
    slug = models.SlugField()

    class Meta:
        ordering = ('name',)
        verbose_name_plural = 'Categories'
        
    def __str__(self):
        return self.name

class Product(models.Model):
    category = models.ForeignKey(Category, related_name='products', on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    slug = models.SlugField()
    description = models.TextField(blank=True, null=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    stock = models.IntegerField(default=0)
    size_options = models.CharField(max_length=250, blank=True, null=True, help_text='Comma-separated sizes like S,M,L,XL')
    image = models.ImageField(upload_to='uploads/', blank=True, null=True)
    thumbnail = models.ImageField(upload_to='uploads/', blank=True, null=True)
    date_added = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ('-date_added',)
        
    def __str__(self):
        return self.name

    # 🌟 ADD THESE THREE FUNCTIONS BELOW: 
    # This generates clean URL strings that serializers look for automatically!
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


# --- NEW: CHECKOUT & STRIPE MODELS ---
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
    price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.IntegerField(default=1)

    def __str__(self):
        size_text = f" ({self.size})" if self.size else ''
        return f"{self.quantity} x {self.product.name}{size_text}"
    
class UserProfile(models.Model):
    # Links directly to a specific Django User account
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    
    # Saved checkout defaults
    phone = models.CharField(max_length=50, blank=True, null=True)
    address = models.CharField(max_length=255, blank=True, null=True)
    zipcode = models.CharField(max_length=50, blank=True, null=True)
    place = models.CharField(max_length=100, blank=True, null=True)

    def __str__(self):
        return f"Profile for {self.user.username}"

# 🌟 AUTOMATION MAGIC: These signals automatically create a blank profile 
# the exact moment a new user signs up on your site!
@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    instance.profile.save()