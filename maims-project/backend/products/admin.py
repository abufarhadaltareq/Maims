from django.contrib import admin
from .models import Category, Collection, Product, ProductMedia, CurrencyPrice

class ProductMediaInline(admin.TabularInline):
    model = ProductMedia
    extra = 1

# 🌟 Inline addition for regional prices
class CurrencyPriceInline(admin.TabularInline):
    model = CurrencyPrice
    extra = 2  # Shows two default blank slots for currencies immediately

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'parent', 'slug']
    prepopulated_fields = {'slug': ('name',)}

@admin.register(Collection)
class CollectionAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'is_active']
    prepopulated_fields = {'slug': ('name',)}

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'brand_name', 'fabric_type', 'stitching_type', 'material_type', 'stock']
    list_filter = ['category', 'collection']
    search_fields = ['name', 'brand_name']
    prepopulated_fields = {'slug': ('name',)}
    
    # Combined multi-media and multi-price inputs together
    inlines = [ProductMediaInline, CurrencyPriceInline]