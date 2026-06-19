from rest_framework import serializers
from .models import UserProfile, Category, Product, Order, OrderItem, ProductMedia

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name', 'slug']

class ProductMediaSerializer(serializers.ModelSerializer):
    url = serializers.SerializerMethodField()

    class Meta:
        model = ProductMedia
        fields = ['id', 'media_type', 'title', 'url']

    def get_url(self, obj):
        return obj.get_url()


class ProductSerializer(serializers.ModelSerializer):
    # This nests the category details inside the product, so Vue gets the category name instead of just an ID number
    category = CategorySerializer(read_only=True)
    size_options = serializers.ListField(child=serializers.CharField(), source='get_size_options', read_only=True)
    media = ProductMediaSerializer(many=True, read_only=True)
    in_stock = serializers.BooleanField(source='is_in_stock', read_only=True)

    class Meta:
        model = Product
        fields = [
            'id', 
            'category', 
            'name', 
            'slug', 
            'description', 
            'price', 
            'stock', 
            'in_stock',
            'size_options',
            'media',
            'date_added',
            'get_image',      # 👈 Exposes the main image url string
            'get_thumbnail'   # 👈 Exposes the thumbnail image url string
        ]

# 🌟 NEW: Added Order Serializers right below your product serializers
class OrderItemSerializer(serializers.ModelSerializer):
    # 🌟 NEW: Nest the full ProductSerializer here! 
    # This automatically unlocks product.name, product.slug, product.get_thumbnail, etc.
    product = ProductSerializer(read_only=True)

    class Meta:
        model = OrderItem
        fields = ['id', 'product', 'size', 'price', 'quantity'] # Cleaned up product_name since it's now inside 'product'

class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)

    class Meta:
        model = Order
        fields = [
            'id', 'first_name', 'last_name', 'email', 'phone', 
            'address', 'zipcode', 'place', 'total_amount', 
            'is_paid', 'stripe_payment_intent_id', 'created_at', 'items'
        ]

class UserProfileSerializer(serializers.ModelSerializer):
    # Pull fields directly from the related User model so we have them in one place
    username = serializers.CharField(source='user.username', read_only=True)
    email = serializers.CharField(source='user.email', read_only=True)

    class Meta:
        model = UserProfile
        fields = ['username', 'email', 'phone', 'address', 'zipcode', 'place']