from rest_framework import serializers
from .models import Product, Category, CurrencyPrice, Order, OrderItem, UserProfile, ProductMedia

# 1. Currency Price Serializer
class CurrencyPriceSerializer(serializers.ModelSerializer):
    class Meta:
        model = CurrencyPrice
        fields = ('currency', 'price')


# 2. Category Serializer
class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ("id", "name", "slug")


# 3. Product Media Serializer (For Multiple Gallery Images/Videos)
class ProductMediaSerializer(serializers.ModelSerializer):
    url = serializers.CharField(source='get_url', read_only=True)

    class Meta:
        model = ProductMedia
        fields = ('id', 'media_type', 'title', 'url', 'order')


# 4. Product Serializer
class ProductSerializer(serializers.ModelSerializer):
    prices = CurrencyPriceSerializer(many=True, read_only=True)
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
        fields = (
            "id", "first_name", "last_name", "email", "phone",
            "address", "zipcode", "place", "total_amount",
            "stripe_payment_intent_id", "is_paid", "created_at", "items"
        )


# 7. User Profile Serializer
class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = ("id", "phone", "address", "zipcode", "place")