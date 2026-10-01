from django.contrib import admin
from django.utils.html import format_html
from .models import Category, Collection, HeroSlide, Order, OrderItem, Product, ProductMedia, CurrencyPrice, SiteSettings, UserProfile

CURRENCY_SYMBOLS = {'USD': '$', 'EUR': '€', 'SEK': 'kr', 'BDT': '৳', 'PKR': 'Rs'}


class ProductMediaInline(admin.TabularInline):
    model = ProductMedia
    extra = 1
    fields = ('media_type', 'title', 'file', 'external_url', 'order')

# 🌟 Inline addition for regional prices
class CurrencyPriceInline(admin.TabularInline):
    model = CurrencyPrice
    extra = 2  # Shows two default blank slots for currencies immediately

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['thumb', 'name', 'parent', 'slug', 'product_count', 'show_on_homepage', 'homepage_order']
    list_filter = ['parent', 'show_on_homepage']
    list_editable = ['show_on_homepage', 'homepage_order']
    search_fields = ['name', 'slug']
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ['image_preview']
    fieldsets = (
        ('Basics', {'fields': ('name', 'slug', 'parent', 'description')}),
        ('Homepage showcase', {'fields': ('show_on_homepage', 'homepage_order', 'image', 'image_preview')}),
    )

    def product_count(self, obj):
        return obj.products.count()
    product_count.short_description = 'Products'

    def thumb(self, obj):
        url = obj.get_image()
        if url:
            return format_html('<img src="{}" style="width:48px;height:48px;object-fit:cover;border-radius:8px;" />', url)
        return '—'
    thumb.short_description = 'Img'

    def image_preview(self, obj):
        url = obj.get_image()
        if url:
            return format_html('<img src="{}" style="max-width:300px;border-radius:12px;" />', url)
        return 'No image uploaded yet.'
    image_preview.short_description = 'Preview'


@admin.register(HeroSlide)
class HeroSlideAdmin(admin.ModelAdmin):
    list_display = ['thumb', 'title', 'order', 'is_active', 'button_text']
    list_editable = ['order', 'is_active']
    list_filter = ['is_active']
    search_fields = ['title', 'subtitle']
    readonly_fields = ['image_preview']
    fieldsets = (
        ('Content', {'fields': ('title', 'subtitle', 'button_text', 'button_link')}),
        ('Background image', {'fields': ('image', 'external_image_url', 'image_preview'),
                              'description': 'Upload an image OR paste an external https:// URL. Upload wins if both are set.'}),
        ('Ordering', {'fields': ('order', 'is_active')}),
    )

    def thumb(self, obj):
        url = obj.get_image_url()
        if url:
            return format_html('<img src="{}" style="width:96px;height:48px;object-fit:cover;border-radius:8px;" />', url)
        return '—'
    thumb.short_description = 'Slide'

    def image_preview(self, obj):
        url = obj.get_image_url()
        if url:
            return format_html('<img src="{}" style="max-width:500px;border-radius:12px;" />', url)
        return 'No image yet — upload one or paste an external URL.'
    image_preview.short_description = 'Preview'

@admin.register(Collection)
class CollectionAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'is_active', 'product_count']
    list_filter = ['is_active']
    search_fields = ['name', 'slug']
    prepopulated_fields = {'slug': ('name',)}

    def product_count(self, obj):
        return obj.products.count()
    product_count.short_description = 'Products'

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['thumb', 'name', 'category', 'price_preview', 'stock_badge', 'in_stock_now']
    list_filter = ['category', 'collection', 'fabric_type', 'stitching_type']
    search_fields = ['name', 'slug', 'brand_name', 'description']
    prepopulated_fields = {'slug': ('name',)}
    list_select_related = ['category', 'collection']
    readonly_fields = ['date_added']
    fieldsets = (
        ('Basics', {'fields': ('name', 'slug', 'brand_name', 'category', 'collection', 'description')}),
        ('Attributes', {'fields': ('fabric_type', 'stitching_type', 'material_type', 'size_options')}),
        ('Inventory & images', {'fields': ('stock', 'image', 'thumbnail', 'date_added')}),
    )

    # Combined multi-media and multi-price inputs together
    inlines = [CurrencyPriceInline, ProductMediaInline]

    def thumb(self, obj):
        url = obj.get_thumbnail()
        if url:
            return format_html('<img src="{}" style="width:48px;height:48px;object-fit:cover;border-radius:8px;" />', url)
        return '—'
    thumb.short_description = 'Img'

    def price_preview(self, obj):
        parts = [f"{CURRENCY_SYMBOLS.get(p.currency, p.currency)} {p.price} {p.currency}" for p in obj.prices.all()[:4]]
        return ' · '.join(parts) if parts else format_html('<span style="color:#b91c1c;">⚠ no price — checkout will fail</span>')
    price_preview.short_description = 'Prices'

    def stock_badge(self, obj):
        color = '#047857' if (obj.stock or 0) > 0 else '#b91c1c'
        return format_html('<b style="color:{};">{} units</b>', color, obj.stock)
    stock_badge.short_description = 'Stock'

    def in_stock_now(self, obj):
        return obj.is_in_stock
    in_stock_now.boolean = True
    in_stock_now.short_description = 'In stock'


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ['product', 'size', 'stitching_selected', 'price', 'quantity', 'line_total']
    fields = ['product', 'size', 'stitching_selected', 'price', 'quantity', 'line_total']
    can_delete = False

    def line_total(self, obj):
        if obj.pk:
            return f"{(obj.price or 0) * (obj.quantity or 0):.2f}"
        return '—'
    line_total.short_description = 'Line total'


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['id', 'customer', 'place', 'total_amount', 'currency', 'method_badge', 'paid_badge', 'created_at']
    list_filter = ['is_paid', 'payment_method', 'currency', 'created_at', 'place']
    search_fields = ['first_name', 'last_name', 'email', 'phone', 'stripe_payment_intent_id']
    readonly_fields = ['stripe_payment_intent_id', 'total_amount', 'created_at']
    date_hierarchy = 'created_at'
    inlines = [OrderItemInline]
    actions = ['mark_paid', 'mark_unpaid']

    def customer(self, obj):
        return f"{obj.first_name} {obj.last_name}"
    customer.short_description = 'Customer'

    def method_badge(self, obj):
        colors = {'stripe': '#1d4ed8', 'cod': '#047857', 'whatsapp': '#16a34a'}
        label = {'stripe': 'CARD', 'cod': 'COD', 'whatsapp': 'WHATSAPP'}.get(obj.payment_method, obj.payment_method)
        return format_html('<b style="color:{};">{}</b>', colors.get(obj.payment_method, '#111'), label)
    method_badge.short_description = 'Method'

    def paid_badge(self, obj):
        if obj.is_paid:
            return format_html('<span style="background:#dcfce7;color:#166534;padding:2px 10px;border-radius:999px;font-weight:700;">PAID</span>')
        return format_html('<span style="background:#fef3c7;color:#92400e;padding:2px 10px;border-radius:999px;font-weight:700;">UNPAID</span>')
    paid_badge.short_description = 'Status'

    def mark_paid(self, request, queryset):
        queryset.update(is_paid=True)
    mark_paid.short_description = 'Mark selected orders as PAID'

    def mark_unpaid(self, request, queryset):
        queryset.update(is_paid=False)
    mark_unpaid.short_description = 'Mark selected orders as UNPAID'


@admin.register(SiteSettings)
class SiteSettingsAdmin(admin.ModelAdmin):
    list_display = ['__str__', 'stripe_enabled', 'cod_enabled', 'whatsapp_enabled',
                    'instagram_url', 'twitter_url', 'updated_at']
    fieldsets = (
        ('Facebook', {'fields': ('facebook_page_url', 'facebook_shop_url'),
                      'description': 'Shown as header/footer buttons and on product pages.'}),
        ('Social links', {'fields': ('instagram_url', 'tiktok_url', 'twitter_url', 'youtube_url', 'linkedin_url'),
                          'description': 'Extra social buttons. Leave a field blank to hide it on the storefront.'}),
        ('WhatsApp Business', {'fields': ('whatsapp_enabled', 'whatsapp_number', 'whatsapp_greeting'),
                               'description': 'Number must be digits only with country code, e.g. 351912345678. Powers Order-via-WhatsApp + floating chat button.'}),
        ('Payments', {'fields': ('stripe_enabled', 'cod_enabled'),
                      'description': 'Toggle checkout methods without touching code.'}),
    )

    def has_add_permission(self, request):
        return not SiteSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'email', 'phone', 'place']
    search_fields = ['user__username', 'user__email', 'phone', 'place']
    list_select_related = ['user']

    def email(self, obj):
        return obj.user.email
    email.short_description = 'Email'