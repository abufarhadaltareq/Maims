from rest_framework import serializers
from .models import (
    Product, Category, CurrencyPrice, CustomerNotificationSettings, HeroBannerSettings, HeroSlide, Order, OrderItem, ProductMedia,
    Review, SiteSettings, UserProfile, WishlistItem,
)

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
        fields = ("id", "title", "subtitle", "badge_text", "button_text", "button_link", "image_url", "order", "is_active")


class HeroBannerSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = HeroBannerSettings
        fields = (
            'hero_enabled', 'height_preset', 'overlay_strength', 'kenburns_intensity',
            'hero_3d_enabled', 'hero_3d_opacity', 'hero_3d_blend',
            'rotation_seconds', 'transition_ms', 'autoplay',
            'accent_color',
        )


class CategorySerializer(serializers.ModelSerializer):
    product_count = serializers.SerializerMethodField()
    children = serializers.SerializerMethodField()
    image_url = serializers.CharField(source='get_image', read_only=True)

    class Meta:
        model = Category
        fields = ("id", "name", "slug", "parent", "product_count", "children",
                  "image_url", "description", "show_on_homepage", "homepage_order")

    def get_product_count(self, obj):
        # NOTE: this must not be written as
        #   getattr(obj, 'product_count', obj.products.count())
        # because Python evaluates the default argument eagerly — the COUNT query
        # ran on every row even when the annotation was already present, and the
        # result was then thrown away. Splitting the lookup means an annotated
        # queryset costs nothing and only unannotated ones hit the database.
        count = getattr(obj, 'product_count', None)
        if count is not None:
            return count
        return obj.products.count()

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
    color_options = serializers.SerializerMethodField()
    length_options = serializers.SerializerMethodField()
    # Star summary for the product page. `rating_average`/`rating_count` are
    # annotated by the queryset; the fallbacks keep the serializer correct when a
    # product is fetched without those annotations (e.g. admin, signals).
    average_rating = serializers.SerializerMethodField()
    review_count = serializers.SerializerMethodField()

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
            "color_options",
            "length_options",
            "media",          # Resolves empty gallery tray tray issue
            "average_rating",  # Star average shown under the product title
            "review_count",    # Number of published reviews
            "facebook_post_id",    # Present = synced from Facebook Page (drives "Live" badge)
            "facebook_image_url",  # Cloud-hosted FB image (preferred by get_image)
        )

    def get_average_rating(self, obj):
        # `rating_count` is the marker that the queryset was annotated, NOT
        # `rating_average`: Avg() returns None for a product with no reviews, and
        # treating that None as "not annotated" sent every unrated product down
        # the per-product query fallback — turning a 5-query catalogue page into
        # one query per product.
        annotated_count = getattr(obj, 'rating_count', None)
        if annotated_count is not None:
            average = getattr(obj, 'rating_average', None)
            return round(float(average), 1) if average is not None else None
        # No annotation: fall back to one query for this single product.
        return obj.average_rating

    def get_review_count(self, obj):
        annotated = getattr(obj, 'rating_count', None)
        if annotated is not None:
            return annotated
        return obj.review_count

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

    def get_color_options(self, obj):
        return obj.get_color_options()

    def get_length_options(self, obj):
        return obj.get_length_options()


# 5. Order Item Serializer
class OrderItemSerializer(serializers.ModelSerializer):
    product = ProductSerializer(read_only=True)
    
    class Meta:
        model = OrderItem
        fields = ("id", "product", "product_name", "size", "stitching_selected", "price", "quantity")


# 6. Order Serializer
class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    # The storefront shows a status timeline, so the customer-facing status has to
    # be in the payload. `status_label` is the plain-English form used in the UI.
    status_label = serializers.CharField(source='get_status_display', read_only=True)

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
            "is_paid", "created_at", "items",
            # Fulfilment progress (read-only for the customer).
            "status", "status_label", "tracking_number", "rejection_reason",
        )


class SiteSettingsSerializer(serializers.ModelSerializer):
    whatsapp_link = serializers.SerializerMethodField()
    logo_url = serializers.SerializerMethodField()

    class Meta:
        model = SiteSettings
        fields = (
            "store_name", "logo_url", "tagline", "footer_about", "footer_bottom_note",
            "announcement_enabled", "announcement_messages", "announcement_speed",
            "facebook_page_url", "facebook_shop_url",
            "instagram_url", "tiktok_url", "twitter_url", "youtube_url", "linkedin_url",
            "whatsapp_number", "whatsapp_enabled", "whatsapp_greeting",
            "stripe_enabled", "paypal_enabled", "whatsapp_link",
        )

    def get_whatsapp_link(self, obj):
        return obj.whatsapp_link()

    def get_logo_url(self, obj):
        logo = getattr(obj, 'logo', None)
        if not logo:
            return ''
        try:
            return logo.url
        except Exception:
            return ''


# 6b. Customer notification (email marketing) settings
class CustomerNotificationSettingsSerializer(serializers.ModelSerializer):
    """Read-only view of the consent row for the storefront.

    `accepts_signups` and `box_starts_ticked` are derived, not stored — the
    frontend must never decide to collect an address from the raw toggles
    alone (a paused shop with forms still flagged 'on' still collects nothing).
    """
    accepts_signups = serializers.BooleanField(read_only=True)
    box_starts_ticked = serializers.BooleanField(read_only=True, source='checkout_box_starts_ticked')

    class Meta:
        model = CustomerNotificationSettings
        fields = (
            "signup_enabled", "checkout_opt_in_enabled", "opt_in_strategy",
            "consent_text", "accepts_signups", "box_starts_ticked",
        )
        read_only_fields = fields


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

# --- REVIEWS ---

class ReviewSummarySerializer(serializers.Serializer):
    """Product-level rating summary embedded in the product payload."""
    average = serializers.FloatField(read_only=True)
    count = serializers.IntegerField(read_only=True)


class ReviewSerializer(serializers.ModelSerializer):
    """
    One customer review.

    `is_verified_purchase` is derived from the linked delivered order rather than
    being settable, so a client cannot simply POST is_verified_purchase=true.
    The author is deliberately reduced to first name + last initial: reviews carry
    social proof without publishing a customer's full name.
    """

    product_slug = serializers.CharField(source='product.slug', read_only=True)
    author = serializers.CharField(source='reviewer_name', read_only=True)
    is_verified_purchase = serializers.BooleanField(read_only=True)
    created_at = serializers.DateTimeField(read_only=True)

    class Meta:
        model = Review
        fields = ('id', 'product_slug', 'author', 'rating', 'title', 'comment',
                  'is_verified_purchase', 'created_at')
        read_only_fields = ('id', 'product_slug', 'author', 'is_verified_purchase',
                            'created_at')

    def validate_rating(self, value):
        if not 1 <= value <= 5:
            raise serializers.ValidationError('Please choose between 1 and 5 stars.')
        return value

    def validate_comment(self, value):
        value = (value or '').strip()
        if not value:
            raise serializers.ValidationError('Please write a short comment.')
        if len(value) > 2000:
            raise serializers.ValidationError('Please keep your review under 2000 characters.')
        return value


class ReviewCreateSerializer(serializers.Serializer):
    """Write path, where rating and comment arrive as plain request data."""

    rating = serializers.IntegerField(min_value=1, max_value=5)
    title = serializers.CharField(max_length=120, required=False, allow_blank=True, default='')
    comment = serializers.CharField(allow_blank=True, default='')

    def validate(self, attrs):
        comment = (attrs.get('comment') or '').strip()
        if not comment:
            raise serializers.ValidationError({'comment': 'Please write a short comment.'})
        if len(comment) > 2000:
            raise serializers.ValidationError(
                {'comment': 'Please keep your review under 2000 characters.'})
        attrs['comment'] = comment
        attrs['title'] = (attrs.get('title') or '').strip()
        return attrs



# --- WISHLIST ---

class WishlistItemSerializer(serializers.ModelSerializer):
    """
    One saved product in a customer's wishlist.

    The nested product uses the same ProductSerializer as the catalogue, so the
    wishlist page reuses ProductCard with zero extra mapping. The product is
    read-only: a wishlist row is created from a product id in the request body,
    never from a nested write.
    """

    product = ProductSerializer(read_only=True)

    class Meta:
        model = WishlistItem
        fields = ('id', 'product', 'created_at')
        read_only_fields = ('id', 'product', 'created_at')


class WishlistAddSerializer(serializers.Serializer):
    """Write path: the body carries a product id, not a nested product."""

    product_id = serializers.IntegerField(min_value=1)

