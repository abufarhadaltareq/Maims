from rest_framework import serializers
from .models import Product, Category, CurrencyPrice, HeroSlide, Order, OrderItem, SiteSettings, UserProfile, ProductMedia

# 1. Currency Price Serializer
class CurrencyPriceSerializer(serializers.ModelSerializer):
    class Meta:
        model = CurrencyPrice
        fields = ('currency', 'price')


# 2. Category Serializer
class HeroSlideSerializer(serializers.ModelSerializer):
    image_url = serializers.CharField(source='get_image_url', read_only=True)

    class Meta:
        model = HeroSlide
        fields = ("id", "title", "subtitle", "button_text", "button_link", "image_url", "order", "is_active")


class CategorySerializer(serializers.ModelSerializer):
    product_count = serializers.SerializerMethodField()
    children = serializers.SerializerMethodField()
    image_url = serializers.CharField(source='get_image', read_only=True)

    class Meta:
        model = Category
        fields = ("id", "name", "slug", "parent", "product_count", "children",
                  "image_url", "description", "show_on_homepage", "homepage_order")

    def get_product_count(self, obj):
        return getattr(obj, 'product_count', obj.products.count())

    def get_children(self, obj):
        children = getattr(obj, '_prefetched_children', None)
        if children is None:
            children = obj.children.all()
        return [{"id": c.id, "name": c.name, "slug": c.slug} for c in children]


# 3. Product Media Serializer (For Multiple Gallery Images/Videos)
class ProductMediaSerializer(serializers.ModelSerializer):
    url = serializers.CharField(source='get_url', read_only=True)

    class Meta:
        model = ProductMedia
        fields = ('id', 'media_type', 'title', 'url', 'order')


# 4. Product Serializer
class ProductSerializer(serializers.ModelSerializer):
    prices = CurrencyPriceSerializer(many=True, read_only=True)
    price = serializers.SerializerMethodField()
    get_image = serializers.ReadOnlyField()
    get_thumbnail = serializers.ReadOnlyField()
    category = CategorySerializer(read_only=True)
    
    # Nested representation of additional images/videos using the related_name='media'
    media = ProductMediaSerializer(many=True, read_only=True)
    
    # Maps properties computed dynamically at the model layer
    in_stock = serializers.BooleanField(source='is_in_stock', read_only=True)
    size_options = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = (
            "id",
            "name",
            "slug",
            "brand_name",
            "description",
            "get_image",
            "get_thumbnail",
            "stock",
            "price",
            "in_stock",       # Unlocks the "Add to Cart" button on frontend
            "date_added",     # Displays creation timestamp
            "category",       # Resolves "Unassigned" fallback layout issue
            "fabric_type",
            "stitching_type",
            "material_type",
            "prices",
            "size_options",   # Passes clean parsed array list strings
            "media",          # Resolves empty gallery tray tray issue
        )

    def get_price(self, obj):
        currency = None
        request = self.context.get('request') if hasattr(self, 'context') else None
        if request is not None:
            currency = request.query_params.get('currency')
        price = obj.get_price(currency or 'EUR')
        return str(price) if price is not None else None

    def get_size_options(self, obj):
        # Calls the model helper method to safely transform comma-split strings to arrays
        return obj.get_size_options()


# 5. Order Item Serializer
class OrderItemSerializer(serializers.ModelSerializer):
    product = ProductSerializer(read_only=True)
    
    class Meta:
        model = OrderItem
        fields = ("id", "product", "size", "stitching_selected", "price", "quantity")


# 6. Order Serializer
class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)

    class Meta:
        model = Order
        # NOTE: `stripe_payment_intent_id` is intentionally NOT exposed. It is a
        # capability token: whoever holds it can drive /checkout/confirm/. It is
        # also never needed by the storefront (the browser gets the id straight
        # from Stripe.js), so echoing it in API responses only widens the blast
        # radius of any future leak. Admin keeps it via ModelAdmin.readonly_fields.
        fields = (
            "id", "first_name", "last_name", "email", "phone",
            "address", "zipcode", "place", "total_amount", "currency",
            "payment_method",
            "is_paid", "created_at", "items"
        )


class SiteSettingsSerializer(serializers.ModelSerializer):
    whatsapp_link = serializers.SerializerMethodField()

    class Meta:
        model = SiteSettings
        fields = (
            "facebook_page_url", "facebook_shop_url",
            "instagram_url", "tiktok_url", "twitter_url", "youtube_url", "linkedin_url",
            "whatsapp_number", "whatsapp_enabled", "whatsapp_greeting",
            "cod_enabled", "stripe_enabled", "whatsapp_link",
        )

    def get_whatsapp_link(self, obj):
        return obj.whatsapp_link()


# 7. User Profile Serializer
class UserProfileSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)
    email = serializers.EmailField(source='user.email', read_only=True)
    first_name = serializers.CharField(source='user.first_name', read_only=True)
    last_name = serializers.CharField(source='user.last_name', read_only=True)

    class Meta:
        model = UserProfile
        fields = ("id", "username", "email", "first_name", "last_name", "phone", "address", "zipcode", "place")


# --- 8. Auth serializers: keep validation in one place ---

class RegisterSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150)
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=8)
    first_name = serializers.CharField(max_length=30, required=False, allow_blank=True, default='')
    last_name = serializers.CharField(max_length=30, required=False, allow_blank=True, default='')

    def validate_username(self, value):
        from django.contrib.auth.models import User
        value = value.strip()
        if not value:
            raise serializers.ValidationError('Username is required.')
        if User.objects.filter(username__iexact=value).exists():
            raise serializers.ValidationError('This username is already taken.')
        return value

    def validate_email(self, value):
        from django.contrib.auth.models import User
        value = value.strip().lower()
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError('An account with this email already exists.')
        return value

    def validate_password(self, value):
        from django.contrib.auth.password_validation import validate_password
        validate_password(value)
        return value

    def create(self, validated_data):
        from django.contrib.auth.models import User
        user = User.objects.create_user(
            username=validated_data['username'].strip(),
            email=validated_data['email'].strip().lower(),
            password=validated_data['password'],
            first_name=validated_data.get('first_name', '').strip(),
            last_name=validated_data.get('last_name', '').strip(),
        )
        return user


class UserSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    username = serializers.CharField(read_only=True)
    email = serializers.EmailField(read_only=True)
    first_name = serializers.CharField(read_only=True)
    last_name = serializers.CharField(read_only=True)