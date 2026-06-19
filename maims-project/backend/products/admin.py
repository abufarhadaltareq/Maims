from django.contrib import admin
from .models import Category, Product, Order, OrderItem, ProductMedia

# Keep your existing Category and Product registrations if they are already here!
@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug']
    prepopulated_fields = {'slug': ('name',)}

class ProductMediaInline(admin.TabularInline):
    model = ProductMedia
    extra = 1
    fields = ['media_type', 'title', 'file', 'external_url', 'order']


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'price', 'stock', 'date_added', 'size_options']
    list_editable = ['price', 'stock']
    prepopulated_fields = {'slug': ('name',)}
    inlines = [ProductMediaInline]
    search_fields = ['name', 'slug', 'description', 'size_options']
    list_filter = ['stock']


# 🌟 NEW: Show Order Items inside the Order detail page cleanly
class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ['product', 'price', 'quantity']


# 🌟 NEW: Customize how Orders appear in your Admin list view
@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['id', 'first_name', 'last_name', 'email', 'total_amount', 'is_paid', 'created_at']
    list_filter = ['is_paid', 'created_at']
    search_fields = ['id', 'first_name', 'last_name', 'email', 'stripe_payment_intent_id']
    ordering = ['-created_at']
    inlines = [OrderItemInline]