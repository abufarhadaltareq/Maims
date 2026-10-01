"""Admin for the storefront, organised around the shop's daily work.

The three jobs that fill a working day are, in order:

1. **Process orders** — see what is waiting, move it forward in one click, print a
   packing slip, contact the customer. (`OrderAdmin`)
2. **Update the catalogue** — change stock and prices from the list page, restock in
   bulk, import or export a price list. (`ProductAdmin`)
3. **Look after customers** — their orders, what they have spent, how to reach them.
   (`core.admin.MaimsUserAdmin`)

Design rules followed throughout:
- Anything done daily is reachable in one click from a list page.
- The list page shows the decision-relevant column (what/who/how much/next step)
  so nobody has to open a record to know what to do.
- Nothing destructive or surprising happens without a confirmation.
- Display columns never crash the page: every one is a real field or a method
  decorated with @admin.display.
"""
import csv
import io
import os
from decimal import Decimal, InvalidOperation

from django import forms
from django.contrib import admin, messages
from django.core.exceptions import PermissionDenied
from django.core.files.storage import default_storage
from django.db import transaction
from django.db.models import Count, F
from django.http import HttpResponse, HttpResponseRedirect
from django.template.response import TemplateResponse
from django.urls import path, reverse
from django.utils import timezone
from django.utils.html import escape, format_html
from django.utils.safestring import mark_safe
from urllib.parse import quote

from core.admin_site import maims_admin

from .models import (
    RESTOCK_LEVEL, Category, Collection, CurrencyPrice, HeroSlide, Order, OrderItem,
    Product, ProductMedia, SiteSettings,
)

CURRENCY_SYMBOLS = {'USD': '$', 'EUR': '€', 'SEK': 'kr', 'BDT': '৳', 'PKR': 'Rs'}
CURRENCY_CODES = tuple(CURRENCY_SYMBOLS)

PAYMENT_COLORS = {
    'stripe': ('#1d4ed8', '#dbeafe'),
    'cod': ('#047857', '#d1fae5'),
    'whatsapp': ('#15803d', '#dcfce7'),
}
PAYMENT_LABELS = {'stripe': 'Card', 'cod': 'Cash on delivery', 'whatsapp': 'WhatsApp'}

STITCHING_LABELS = dict(Product.STITCHING_CHOICES)

# What "the next step" is for an order, used by the one-click advance button and by
# the reminder text on the order page. Terminal states have no next step.
NEXT_STATUS = {'new': 'packed', 'packed': 'shipped', 'shipped': 'delivered'}
NEXT_STATUS_LABEL = {'new': 'Pack it', 'packed': 'Ship it', 'shipped': 'Mark delivered'}


# --- small presentational helpers -------------------------------------------------

def money(amount, currency=''):
    """Format an amount, e.g. money(120, 'EUR') -> '€120.00 EUR'."""
    if amount is None:
        return '—'
    symbol = CURRENCY_SYMBOLS.get(currency, '')
    return f"{symbol}{amount} {currency}".strip()


def badge(text, colors):
    """Coloured pill used in list columns. Values are escaped by format_html."""
    fg, bg = colors
    return format_html(
        '<span class="maims-badge" style="color:{};background-color:{};">{}</span>', fg, bg, text,
    )


def thumbnail(url, width=48, height=48, radius=8):
    if not url:
        return mark_safe('<span class="maims-nothumb">no image</span>')
    return format_html(
        '<img src="{}" style="width:{}px;height:{}px;object-fit:cover;border-radius:{}px;" loading="lazy" />',
        url, width, height, radius,
    )


def unique_slug(model, base):
    """Return `base`, or `base-2`, `base-3`... so a slug is never duplicated.

    Product pages are looked up with .get(slug=...), so a duplicated slug would
    make the storefront raise MultipleObjectsReturned on that URL.
    """
    base = base or 'item'
    slug = base
    suffix = 2
    while model.objects.filter(slug=slug).exists():
        slug = f"{base}-{suffix}"
        suffix += 1
    return slug


def order_age(order):
    """Human age of an order: '4m', '4h', '3d', '2w' — for triaging the queue.

    Returns '—' for an unsaved order, which the admin renders on the add form.
    """
    if not order.created_at:
        return '—'
    seconds = (timezone.now() - order.created_at).total_seconds()
    if seconds < 3600:
        return f"{int(seconds // 60)}m"
    if seconds < 86400:
        return f"{int(seconds // 3600)}h"
    if seconds < 604800:
        return f"{int(seconds // 86400)}d"
    return f"{int(seconds // 604800)}w"


def whatsapp_link(phone, message):
    """wa.me link with a prefilled message, or '' when the number is unusable."""
    digits = ''.join(ch for ch in (phone or '') if ch.isdigit())
    if not digits:
        return ''
    return f"https://wa.me/{digits}?text={quote(message or '')}"


class MaimsModelAdmin(admin.ModelAdmin):
    """Defaults every shop admin inherits: roomier lists, action bar on top, nicer empties."""
    save_on_top = True
    actions_on_top = True
    actions_on_bottom = False
    list_per_page = 30
    list_max_show_all = 300
    show_full_result_count = False
    empty_value_display = '—'


# --- orders ------------------------------------------------------------------------

class OrderItemInline(admin.TabularInline):
    """What was ordered. Read-only: prices come from the catalogue, not from the admin."""
    model = OrderItem
    extra = 0
    can_delete = False
    fields = ('product', 'size', 'stitching_selected', 'price', 'quantity', 'line_total')
    readonly_fields = fields
    verbose_name_plural = 'Items ordered'

    @admin.display(description='Product')
    def product(self, obj):
        if not obj.product_id:
            return '—'
        url = reverse('admin:products_product_change', args=[obj.product_id])
        return format_html('<a href="{}">{}</a>', url, obj.product.name)

    @admin.display(description='Size')
    def size(self, obj):
        return obj.size or 'One size'

    @admin.display(description='Stitching')
    def stitching_selected(self, obj):
        return STITCHING_LABELS.get(obj.stitching_selected, obj.stitching_selected)

    @admin.display(description='Price each')
    def price(self, obj):
        return obj.price if obj.pk else '—'

    @admin.display(description='Qty')
    def quantity(self, obj):
        return obj.quantity if obj.pk else '—'

    @admin.display(description='Line total')
    def line_total(self, obj):
        return obj.line_total if obj.pk else '—'


class RestockForm(forms.Form):
    """Intermediate page for the bulk restock action."""
    new_stock = forms.IntegerField(
        min_value=0, max_value=100000, initial=10,
        label='Set stock of every selected product to',
        help_text='This replaces the current number, it does not add to it. '
                  'Use the "+" action on a single product to add stock instead.',
    )
    only_if_lower = forms.BooleanField(
        required=False, initial=True,
        label='Only raise stock, never lower it',
        help_text='Tick this to restock sold-out and low items without touching healthy stock.',
    )


class TrackingNumberForm(forms.Form):
    """Intermediate page for the "set tracking number" bulk action."""
    tracking_number = forms.CharField(
        label='Tracking / courier reference', max_length=120,
        help_text='Saved on every selected order, which are also switched to "Shipped".',
    )


class OrderAdmin(MaimsModelAdmin):
    change_form_template = 'admin/maims_change_form.html'
    list_display = ('order_ref', 'age', 'customer', 'items_summary', 'total_display',
                    'payment_badge', 'status', 'is_paid', 'next_step')
    list_display_links = ('order_ref',)
    list_filter = ('status', 'is_paid', 'payment_method', 'currency', 'created_at')
    list_editable = ('status',)
    date_hierarchy = 'created_at'
    ordering = ('-created_at',)
    search_fields = ('=id', 'first_name', 'last_name', 'email', 'phone', 'tracking_number',
                     'stripe_payment_intent_id', 'admin_note')
    autocomplete_fields = ('user',)
    readonly_fields = ('order_ref', 'age', 'created_at', 'total_amount',
                       'stripe_payment_intent_id', 'items_block', 'contact_customer')
    inlines = (OrderItemInline,)
    fieldsets = (
        ('Order', {
            'fields': ('order_ref', 'age', 'created_at', 'items_block', 'contact_customer'),
            'description': 'Totals and prices are calculated at checkout and cannot be edited here.'}),
        ('Customer', {
            'fields': ('user', 'first_name', 'last_name', 'email', 'phone',
                       'address', 'zipcode', 'place')}),
        ('Payment', {
            'fields': ('total_amount', 'currency', 'payment_method', 'is_paid', 'stripe_payment_intent_id'),
            'description': 'Card payments are confirmed by Stripe automatically. If a status looks wrong, '
                           'fix it with the actions on the orders list.'}),
        ('Fulfilment', {
            'fields': ('status', 'tracking_number'),
            'description': 'Set the status here, or use the one-click button on the orders list.'}),
        ('Internal only', {'fields': ('admin_note',)}),
    )
    actions = ('mark_paid', 'mark_unpaid', 'mark_packed', 'mark_shipped', 'mark_delivered',
               'cancel_orders', 'set_tracking_number', 'print_packing_slips')

    def get_urls(self):
        # One-click "advance this order to its next step" from the list page.
        return [
            path('<path:object_id>/advance/',
                 self.admin_site.admin_view(self.advance_view),
                 name='products_order_advance'),
            path('<path:object_id>/packing-slip/',
                 self.admin_site.admin_view(self.packing_slip_view),
                 name='products_order_packing_slip'),
        ] + super().get_urls()

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user').prefetch_related('items__product')

    def get_changelist_instance(self, request):
        # The next-step button is rendered per row, so it must not appear at all
        # for a user who may only view orders.
        self.has_change_permission_cache = self.has_change_permission(request)
        return super().get_changelist_instance(request)

    def changelist_view(self, request, extra_context=None):
        """Add one-click filter presets above the list — the queues people work from."""
        extra_context = extra_context or {}
        extra_context['order_presets'] = self._presets()
        return super().changelist_view(request, extra_context)

    def change_view(self, request, object_id, form_url='', extra_context=None):
        """Put a link to the printable packing slip in the order page's tool row."""
        extra_context = extra_context or {}
        if object_id and self.has_view_permission(request):
            extra_context['packing_slip_url'] = reverse(
                'admin:products_order_packing_slip', args=[object_id])
        return super().change_view(request, object_id, form_url, extra_context)

    def _presets(self):
        base = reverse('admin:products_order_changelist')
        return [
            {'label': 'Waiting to be packed', 'url': f"{base}?status__exact=new"},
            {'label': 'Packed, waiting for courier', 'url': f"{base}?status__exact=packed"},
            {'label': 'In transit', 'url': f"{base}?status__exact=shipped"},
            {'label': 'Payment not confirmed', 'url': f"{base}?is_paid__exact=0"},
            {'label': 'All open orders', 'url': f"{base}?status__exact=new&status__exact=packed&status__exact=shipped"},
        ]

    # --- the one-click status transition

    def advance_view(self, request, object_id):
        """Move a single order to the next step in the fulfilment flow."""
        if not self.has_change_permission(request):
            raise PermissionDenied
        order = self.get_object(request, object_id)
        nxt = NEXT_STATUS.get(order.status)
        if not nxt:
            self.message_user(request, f'Order #{order.pk} is already {order.get_status_display().lower()}.',
                              level=messages.WARNING)
        else:
            order.status = nxt
            order.save(update_fields=['status'])
            extra = ''
            if nxt == 'shipped' and not order.tracking_number:
                extra = ' Add a tracking number before handing it to the courier.'
            self.message_user(request, f'Order #{order.pk} → {order.get_status_display()}.{extra}',
                              level=messages.SUCCESS)
        return HttpResponseRedirect(request.META.get('HTTP_REFERER')
                                    or reverse('admin:products_order_changelist'))

    @admin.display(description='')
    def next_step(self, obj):
        """The single most useful control on the row: push the order forward.

        Rendered as a submit button with `formaction` rather than its own <form>,
        because every row already sits inside the changelist form and nested forms
        are invalid HTML — the browser would drop the inner one.
        """
        if not self.has_change_permission_cache:
            return '—'
        nxt = NEXT_STATUS.get(obj.status)
        if not nxt:
            return mark_safe('<span class="maims-done">done</span>')
        return format_html(
            '<button type="submit" class="maims-next" formaction="{}" formmethod="post" '
            'formnovalidate>{} →</button>',
            reverse('admin:products_order_advance', args=[obj.pk]), NEXT_STATUS_LABEL[obj.status],
        )

    @admin.display(description='Age', ordering='created_at')
    def age(self, obj):
        return order_age(obj)

    # --- list columns

    @admin.display(description='Order', ordering='id')
    def order_ref(self, obj):
        url = reverse('admin:products_order_change', args=[obj.pk])
        return format_html('<strong><a href="{}">#{}</a></strong>', url, obj.pk)

    @admin.display(description='Customer', ordering='last_name')
    def customer(self, obj):
        return format_html(
            '<strong>{} {}</strong><br><span class="maims-muted">{} · {}</span>',
            obj.first_name, obj.last_name, obj.place, obj.phone or obj.email,
        )

    @admin.display(description='Items')
    def items_summary(self, obj):
        items = list(obj.items.all())
        if not items:
            return badge('NO ITEMS', ('#991b1b', '#fee2e2'))
        parts = [
            format_html('{}x {}', item.quantity, item.product.name)
            + (f" ({item.size})" if item.size else '')
            for item in items[:2]
        ]
        summary = mark_safe(', '.join(parts))
        if len(items) > 2:
            summary += f" +{len(items) - 2}"
        return summary

    @admin.display(description='Total', ordering='total_amount')
    def total_display(self, obj):
        return format_html('<strong>{}</strong>', money(obj.total_amount, obj.currency))

    @admin.display(description='Method', ordering='payment_method')
    def payment_badge(self, obj):
        label = PAYMENT_LABELS.get(obj.payment_method, obj.payment_method)
        return badge(label, PAYMENT_COLORS.get(obj.payment_method, ('#111827', '#e5e7eb')))

    @admin.display(boolean=True, description='Paid', ordering='is_paid')
    def is_paid(self, obj):
        return obj.is_paid

    # --- read-only blocks on the order page

    @admin.display(description='Items ordered')
    def items_block(self, obj):
        """Readable summary shown at the top of the order page."""
        if not obj.pk:
            return 'Save the order first to add items.'
        items = list(obj.items.all())
        if not items:
            return mark_safe('<span class="maims-muted">This order has no items.</span>')
        rows = mark_safe(''.join(
            format_html('<li>{} x <a href="{}">{}</a>{} — {}</li>',
                        item.quantity,
                        reverse('admin:products_product_change', args=[item.product_id]),
                        item.product.name,
                        f' ({item.size})' if item.size else '',
                        item.line_total)
            for item in items
        ))
        return mark_safe(
            f'<ul class="maims-items">{rows}</ul>'
            f'<p><strong>Total: {money(obj.total_amount, obj.currency)}</strong></p>'
        )

    @admin.display(description='Contact the customer')
    def contact_customer(self, obj):
        """One-click WhatsApp / email, pre-filled with the order reference."""
        if not obj.pk:
            return 'Save the order first.'
        message = (f"Hello {obj.first_name}, this is Maims about your order #{obj.pk} "
                   f"({money(obj.total_amount, obj.currency)})."
                   + (f" Tracking: {obj.tracking_number}." if obj.tracking_number else ''))
        wa = whatsapp_link(obj.phone, message)
        rows = []
        if wa:
            rows.append(format_html(
                '<a class="maims-contact maims-contact--wa" href="{}" target="_blank" rel="noopener">'
                'WhatsApp {}</a>', wa, obj.phone))
        rows.append(format_html(
            '<a class="maims-contact" href="mailto:{}?subject={}">Email {}</a>',
            obj.email, quote(f'Your Maims order #{obj.pk}'), obj.email))
        return mark_safe(' '.join(rows))

    # --- bulk actions

    def _bulk_set(self, request, queryset, field, value, label):
        changed = queryset.update(**{field: value})
        self.message_user(request, f'{changed} order{"" if changed == 1 else "s"} marked as {label}.',
                          level=messages.SUCCESS)

    @admin.action(description='1. Mark as PAID')
    def mark_paid(self, request, queryset):
        self._bulk_set(request, queryset, 'is_paid', True, 'paid')

    @admin.action(description='2. Mark as UNPAID')
    def mark_unpaid(self, request, queryset):
        self._bulk_set(request, queryset, 'is_paid', False, 'unpaid')

    @admin.action(description='3. Mark as PACKED')
    def mark_packed(self, request, queryset):
        self._bulk_set(request, queryset, 'status', 'packed', 'packed')

    @admin.action(description='4. Mark as SHIPPED')
    def mark_shipped(self, request, queryset):
        self._bulk_set(request, queryset, 'status', 'shipped', 'shipped')

    @admin.action(description='5. Mark as DELIVERED')
    def mark_delivered(self, request, queryset):
        self._bulk_set(request, queryset, 'status', 'delivered', 'delivered')

    @admin.action(description='Cancel selected orders')
    def cancel_orders(self, request, queryset):
        self._bulk_set(request, queryset, 'status', 'cancelled', 'cancelled')

    @admin.action(description='Print packing slips for selected orders')
    def print_packing_slips(self, request, queryset):
        """One printable page per order — batch packing without opening each record."""
        orders = list(queryset.select_related('user').prefetch_related('items__product'))
        if not orders:
            self.message_user(request, 'No orders selected.', level=messages.WARNING)
            return None
        return TemplateResponse(request, 'admin/maims_packing_slips.html', {
            **self.admin_site.each_context(request),
            'title': 'Packing slips',
            'orders': orders,
            'site': SiteSettings.objects.first(),
        })

    @admin.action(description='Set tracking number…')
    def set_tracking_number(self, request, queryset):
        """Ask for one tracking reference, then apply it to every selected order."""
        if 'apply_tracking' in request.POST:
            form = TrackingNumberForm(request.POST)
            if form.is_valid():
                tracking = form.cleaned_data['tracking_number'].strip()
                changed = queryset.update(tracking_number=tracking, status='shipped')
                self.message_user(
                    request,
                    f'Tracking {tracking} saved on {changed} order{"" if changed == 1 else "s"} '
                    'and marked as shipped.',
                    level=messages.SUCCESS,
                )
                return None
        else:
            first = queryset.first()
            form = TrackingNumberForm(initial={'tracking_number': first.tracking_number or ''}
                                      if first else None)

        context = {
            **self.admin_site.each_context(request),
            'title': 'Set tracking number',
            'opts': self.model._meta,
            'queryset': queryset,
            'form': form,
            'action_checkbox_name': admin.helpers.ACTION_CHECKBOX_NAME,
            'media': self.media,
        }
        return TemplateResponse(request, 'admin/maims_action_form.html', context)

    def packing_slip_view(self, request, object_id):
        """A single printable packing slip for one order."""
        if not self.has_view_permission(request):
            raise PermissionDenied
        order = self.get_object(request, object_id)
        context = {
            **self.admin_site.each_context(request),
            'title': f'Packing slip #{order.pk}',
            'order': order,
            'orders': [order],
            'opts': self.model._meta,
            'site': SiteSettings.objects.first(),
        }
        return TemplateResponse(request, 'admin/maims_packing_slips.html', context)


# --- catalogue ---------------------------------------------------------------------

class CurrencyPriceInline(admin.TabularInline):
    model = CurrencyPrice
    extra = 2
    fields = ('currency', 'price')
    verbose_name_plural = 'Price per currency'


class ProductMediaInline(admin.TabularInline):
    model = ProductMedia
    extra = 1
    fields = ('media_type', 'title', 'file', 'external_url', 'order')
    verbose_name_plural = 'Photos & videos'


class StockFilter(admin.SimpleListFilter):
    """The restocking views: what sold out, what is nearly gone, what is healthy."""
    title = 'stock'
    # NOT 'stock': the query parameter must not collide with the integer field, or
    # Django builds stock__exact=out and rejects "out" as a bad integer.
    parameter_name = 'stock_level'

    def lookups(self, request, model_admin):
        return (
            ('out', f'Sold out (0)'),
            ('low', f'Low (1-{RESTOCK_LEVEL})'),
            ('ok', f'Healthy ({RESTOCK_LEVEL + 1}+)'),
        )

    def queryset(self, request, queryset):
        value = self.value()
        if value == 'out':
            return queryset.filter(stock__lte=0)
        if value == 'low':
            return queryset.filter(stock__gte=1, stock__lte=RESTOCK_LEVEL)
        if value == 'ok':
            return queryset.filter(stock__gte=RESTOCK_LEVEL + 1)
        return queryset


class PricingFilter(admin.SimpleListFilter):
    """Products that cannot be bought, because checkout rejects unpriced currencies."""
    title = 'pricing'
    parameter_name = 'pricing'

    def lookups(self, request, model_admin):
        return (('none', 'No price set'), ('partial', 'Only some currencies'))

    def queryset(self, request, queryset):
        value = self.value()
        if value == 'none':
            return queryset.annotate(price_count=Count('prices')).filter(price_count=0)
        if value == 'partial':
            return queryset.annotate(price_count=Count('prices')).filter(
                price_count__gt=0, price_count__lt=len(CURRENCY_SYMBOLS))
        return queryset


class ProductCSVForm(forms.Form):
    """Upload a price/stock sheet. Matched on slug, so existing products are updated."""
    csv_file = forms.FileField(
        label='CSV file',
        help_text='One header row, then one product per row. Columns: '
                  'slug, name, category_slug, brand_name, stock, '
                  + ', '.join(f'price_{code}' for code in CURRENCY_CODES)
                  + ', description. Products are matched on slug; '
                    'a row without a slug is skipped. Leave a column empty to keep the current value.',
    )
    create_missing = forms.BooleanField(
        required=False, initial=True,
        label='Create products that do not exist yet',
        help_text='Unticked, rows with an unknown slug are reported and skipped.',
    )

    def clean_csv_file(self):
        upload = self.cleaned_data['csv_file']
        if upload.size > 2 * 1024 * 1024:
            raise forms.ValidationError('Please upload a file smaller than 2 MB.')
        if not upload.name.lower().endswith('.csv'):
            raise forms.ValidationError('The file must be a .csv file.')
        return upload


class ProductAdmin(MaimsModelAdmin):
    list_display = ('thumb', 'name', 'category', 'stock', 'price_preview', 'is_in_stock',
                    'media_count', 'date_added')
    list_display_links = ('thumb', 'name')
    # Stock is the number that changes daily — edit it straight from the list.
    list_editable = ('stock',)
    list_filter = ('category', 'collection', 'fabric_type', 'stitching_type', StockFilter, PricingFilter)
    search_fields = ('name', 'slug', 'brand_name', 'description')
    prepopulated_fields = {'slug': ('name',)}
    autocomplete_fields = ('category', 'collection')
    list_select_related = ('category', 'collection')
    readonly_fields = ('date_added',)
    date_hierarchy = 'date_added'
    inlines = (CurrencyPriceInline, ProductMediaInline)
    change_list_template = 'admin/maims_changelist.html'
    actions = ('add_stock', 'mark_sold_out', 'restock_selected', 'duplicate_products',
               'export_products_csv')
    change_form_template = 'admin/maims_change_form.html'
    fieldsets = (
        ('Basics', {
            'fields': ('name', 'slug', 'brand_name', 'category', 'collection', 'description'),
            'description': 'The slug becomes the product URL (/products/&lt;slug&gt;) and is what the '
                           'CSV import matches on, so keep it stable once a product is live.'}),
        ('Stock & price', {
            'fields': ('stock', 'image', 'thumbnail', 'date_added'),
            'description': 'Stock 0 removes the "add to cart" button. If the thumbnail is empty the '
                           'main image is used. Prices are set per currency in the table below.'}),
        ('Clothing attributes', {
            'fields': ('fabric_type', 'stitching_type', 'material_type', 'size_options'),
            'description': 'Only needed for clothing. Use <b>material type</b> for bags and jewellery, and '
                           '<b>size options</b> for anything that is not S/M/L (for example "One Size").'}),
    )

    def get_urls(self):
        return [
            path('import-csv/', self.admin_site.admin_view(self.import_csv_view),
                 name='products_product_import_csv'),
            path('export-csv/', self.admin_site.admin_view(self.export_all_csv_view),
                 name='products_product_export_csv'),
        ] + super().get_urls()

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related('prices', 'media')

    def changelist_view(self, request, extra_context=None):
        """Stock warning and the CSV import link above the catalogue list."""
        extra_context = extra_context or {}
        if self.has_view_permission(request):
            extra_context['restock_count'] = Product.objects.filter(
                stock__lte=RESTOCK_LEVEL).count()
            extra_context['restock_level'] = RESTOCK_LEVEL
        extra_context['show_import_link'] = self.has_change_permission(request)
        extra_context['show_export_link'] = self.has_view_permission(request)
        return super().changelist_view(request, extra_context)

    # --- list columns

    @admin.display(description='')
    def thumb(self, obj):
        return thumbnail(obj.get_thumbnail())

    @admin.display(description='Price', ordering='min_price')
    def price_preview(self, obj):
        prices = list(obj.prices.all())
        if not prices:
            return badge('NO PRICE', ('#991b1b', '#fee2e2'))
        summary = ' · '.join(f"{CURRENCY_SYMBOLS.get(p.currency, '')}{p.price}" for p in prices)
        missing = len(CURRENCY_SYMBOLS) - len(prices)
        if missing:
            return format_html('{}{}', summary, badge(f'+{missing} to set', ('#92400e', '#fef3c7')))
        return summary

    @admin.display(boolean=True, description='Buyable', ordering='stock')
    def is_in_stock(self, obj):
        return obj.is_in_stock

    @admin.display(description='Media')
    def media_count(self, obj):
        total = len(obj.media.all())
        return f"{total} file{'' if total == 1 else 's'}"

    # --- stock actions (the daily work)

    @admin.action(description='Add 10 to stock of selected products')
    def add_stock(self, request, queryset):
        changed = queryset.update(stock=F('stock') + 10)
        self.message_user(request, f'Added 10 units to {changed} product{"" if changed == 1 else "s"}.',
                          level=messages.SUCCESS)

    @admin.action(description='Mark selected products as SOLD OUT (stock 0)')
    def mark_sold_out(self, request, queryset):
        changed = queryset.update(stock=0)
        self.message_user(request, f'{changed} product{"" if changed == 1 else "s"} marked sold out.',
                          level=messages.SUCCESS)

    @admin.action(description='Set stock of selected products to…')
    def restock_selected(self, request, queryset):
        """Bulk restock: type the number, tick "only raise" so healthy stock is untouched."""
        if 'apply_restock' in request.POST:
            form = RestockForm(request.POST)
            if form.is_valid():
                new_stock = form.cleaned_data['new_stock']
                if form.cleaned_data['only_if_lower']:
                    queryset = queryset.filter(stock__lt=new_stock)
                changed = queryset.update(stock=new_stock)
                self.message_user(request, f'Stock set to {new_stock} on {changed} product'
                                          f'{"" if changed == 1 else "s"}.', level=messages.SUCCESS)
                return None
        else:
            form = RestockForm()

        context = {
            **self.admin_site.each_context(request),
            'title': 'Set stock',
            'opts': self.model._meta,
            'queryset': queryset,
            'form': form,
            'action_checkbox_name': admin.helpers.ACTION_CHECKBOX_NAME,
            'media': self.media,
        }
        return TemplateResponse(request, 'admin/maims_action_form.html', context)

    @admin.action(description='Duplicate selected products (with prices and media)')
    def duplicate_products(self, request, queryset):
        """Quick way to set up a similar item: copies prices and media, stock starts at 0."""
        created = 0
        for source in queryset:
            copy = Product.objects.create(
                category=source.category,
                collection=source.collection,
                name=f"{source.name} (copy)",
                slug=unique_slug(Product, f"{source.slug}-copy"),
                brand_name=source.brand_name,
                description=source.description,
                fabric_type=source.fabric_type,
                stitching_type=source.stitching_type,
                material_type=source.material_type,
                size_options=source.size_options,
                stock=0,
            )
            for price in source.prices.all():
                CurrencyPrice.objects.create(product=copy, currency=price.currency, price=price.price)
            for media in source.media.all():
                # Give the copy its own file on disk, otherwise both records would point
                # at one upload and deleting one would break the other.
                new_file = None
                if media.file:
                    media.file.open('rb')
                    try:
                        new_file = default_storage.save(
                            f"{copy.slug}-{os.path.basename(media.file.name)}", media.file)
                    finally:
                        media.file.close()
                ProductMedia.objects.create(
                    product=copy, media_type=media.media_type, title=media.title,
                    file=new_file, external_url=media.external_url, order=media.order,
                )
            created += 1
        self.message_user(
            request, f'Created {created} product cop{"y" if created == 1 else "ies"} with stock 0.',
            level=messages.SUCCESS,
        )

    # --- CSV in / out

    EXPORT_COLUMNS = ['slug', 'name', 'category_slug', 'collection_slug', 'brand_name',
                      'stock', 'size_options', 'fabric_type', 'stitching_type',
                      'material_type', 'description',
                      *[f'price_{code}' for code in CURRENCY_CODES]]

    @admin.action(description='Export selected products to CSV')
    def export_products_csv(self, request, queryset):
        """Download the current catalogue, ready to edit in a spreadsheet and re-import."""
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = (
            f'attachment; filename="maims-products-{timezone.localtime().strftime("%Y%m%d-%H%M")}.csv"')
        # utf-8-sig so Excel opens the ৳ and € symbols correctly.
        response.write('﻿')
        writer = csv.writer(response)
        writer.writerow(self.EXPORT_COLUMNS)
        products = list(queryset.select_related('category', 'collection').prefetch_related('prices'))
        for product in products:
            prices = {p.currency: p.price for p in product.prices.all()}
            writer.writerow([
                product.slug, product.name,
                product.category.slug if product.category else '',
                product.collection.slug if product.collection else '',
                product.brand_name or '', product.stock, product.size_options or '',
                product.fabric_type or '', product.stitching_type or '',
                product.material_type or '', product.description or '',
                *[prices.get(code, '') for code in CURRENCY_CODES],
            ])
        self.message_user(request, f'Exported {len(products)} product'
                                   f'{"" if len(products) == 1 else "s"} to CSV.',
                          level=messages.SUCCESS)
        return response

    def export_all_csv_view(self, request):
        """Download the whole catalogue — the starting point for a spreadsheet update."""
        if not self.has_view_permission(request):
            raise PermissionDenied
        return self.export_products_csv(request, self.get_queryset(request))

    def import_csv_view(self, request):
        """Bulk price/stock update from a spreadsheet, matched on slug."""
        if not self.has_change_permission(request):
            raise PermissionDenied

        if request.method == 'POST':
            form = ProductCSVForm(request.POST, request.FILES)
            if form.is_valid():
                report = self._apply_csv(
                    form.cleaned_data['csv_file'],
                    create_missing=form.cleaned_data['create_missing'],
                )
                if report['errors'] and not report['created'] and not report['updated']:
                    form.add_error('csv_file', 'Nothing could be imported — see the report below.')
                    return self._render_import(request, form, report)
                self.message_user(
                    request,
                    f'CSV import finished: {report["created"]} created, '
                    f'{report["updated"]} updated, {report["skipped"]} skipped.',
                    level=messages.SUCCESS if (report['created'] or report['updated'])
                    else messages.WARNING,
                )
                return self._render_import(request, form, report)
        else:
            form = ProductCSVForm()
        return self._render_import(request, form, None)

    def _render_import(self, request, form, report):
        context = {
            **self.admin_site.each_context(request),
            'title': 'Import products from CSV',
            'opts': self.model._meta,
            'form': form,
            'report': report,
            'example_csv': 'slug,name,category_slug,stock,price_EUR\n'
                           'jamdani-100-counts,Jamdani 100 counts,women-clothing,25,1200.00',
        }
        return TemplateResponse(request, 'admin/maims_import_csv.html', context)

    def _apply_csv(self, upload, create_missing=True):
        """Apply a CSV to the catalogue. One transaction: either the sheet applies or it doesn't.

        Returns a per-row report so the operator can see exactly what happened.
        """
        created = updated = skipped = 0
        rows_report = []
        categories = {c.slug: c for c in Category.objects.all()}

        raw = upload.read().decode('utf-8-sig', errors='replace')
        reader = csv.DictReader(io.StringIO(raw))
        if not reader.fieldnames:
            return {'created': 0, 'updated': 0, 'skipped': 1, 'rows': [],
                    'errors': ['The file has no header row.'], 'total': 0}

        if 'slug' not in [f.strip() for f in reader.fieldnames]:
            return {'created': 0, 'updated': 0, 'skipped': 1, 'rows': [],
                    'errors': ['The file must have a "slug" column — it is how rows are matched.'],
                    'total': 0}

        rows = list(reader)
        if len(rows) > 2000:
            return {'created': 0, 'updated': 0, 'skipped': 0, 'rows': [],
                    'errors': ['The file has more than 2000 rows. Split it into smaller sheets.'],
                    'total': len(rows)}

        with transaction.atomic():
            for index, row in enumerate(rows, start=2):  # row 1 is the header
                row = {(k or '').strip().lower(): (v or '').strip() for k, v in row.items()}
                line = f'row {index}'
                try:
                    slug = row.get('slug', '')
                    if not slug:
                        raise ValueError('no slug')

                    product = Product.objects.filter(slug=slug).first()
                    if product is None and not create_missing:
                        raise ValueError('unknown slug, and "create missing" is off')

                    if product is None:
                        category_slug = row.get('category_slug', '')
                        category = categories.get(category_slug) or Category.objects.filter(
                            slug=category_slug).first()
                        if category is None:
                            raise ValueError(f'no category matches "{category_slug}"')
                        prices = _prices_from_row(row)
                        if not prices:
                            raise ValueError('no price given, so it would not be buyable')
                        product = Product.objects.create(
                            slug=slug, name=row.get('name') or slug, category=category,
                            stock=int(row.get('stock') or 0), brand_name=row.get('brand_name') or None,
                            description=row.get('description') or None,
                        )
                        for code, value in prices.items():
                            CurrencyPrice.objects.create(product=product, currency=code, price=value)
                        categories.setdefault(category_slug, category)
                        created += 1
                        rows_report.append((line, slug, 'created'))
                        continue

                    # Update only the columns the sheet actually filled in.
                    changes = []
                    if row.get('name') and row['name'] != product.name:
                        product.name = row['name']
                        changes.append('name')
                    if row.get('brand_name'):
                        product.brand_name = row['brand_name']
                        changes.append('brand')
                    if row.get('description'):
                        product.description = row['description']
                        changes.append('description')
                    if row.get('size_options'):
                        product.size_options = row['size_options']
                        changes.append('sizes')
                    if row.get('stock'):
                        try:
                            new_stock = int(row['stock'])
                        except ValueError:
                            raise ValueError(f'stock "{row["stock"]}" is not a number')
                        if new_stock != product.stock:
                            product.stock = new_stock
                            changes.append(f'stock→{new_stock}')
                    category_slug = row.get('category_slug', '')
                    if category_slug and category_slug != (product.category.slug if product.category else ''):
                        category = categories.get(category_slug) or Category.objects.filter(
                            slug=category_slug).first()
                        if category is None:
                            raise ValueError(f'no category matches "{category_slug}"')
                        product.category = category
                        changes.append('category')

                    if changes:
                        product.save()
                    for code, value in _prices_from_row(row).items():
                        existing = CurrencyPrice.objects.filter(product=product, currency=code).first()
                        if existing:
                            if existing.price != value:
                                existing.price = value
                                existing.save(update_fields=['price'])
                                changes.append(f'{code} price')
                        else:
                            CurrencyPrice.objects.create(product=product, currency=code, price=value)
                            changes.append(f'{code} price (new)')

                    if changes:
                        updated += 1
                        rows_report.append((line, slug, 'updated: ' + ', '.join(changes)))
                    else:
                        skipped += 1
                        rows_report.append((line, slug, 'no change'))

                except ValueError as exc:
                    skipped += 1
                    rows_report.append((line, row.get('slug', '?'), f'SKIPPED — {exc}'))

        errors = [f'Row {line}: {reason}' for line, _slug, reason in rows_report if 'SKIPPED' in reason]
        return {'created': created, 'updated': updated, 'skipped': skipped,
                'rows': rows_report, 'errors': errors, 'total': len(rows)}


def _prices_from_row(row):
    """Pull price_EUR / price_USD / ... out of a CSV row into {code: Decimal}."""
    prices = {}
    for code in CURRENCY_CODES:
        value = row.get(f'price_{code.lower()}', '')
        if value in ('', None):
            continue
        try:
            prices[code] = Decimal(value)
        except (InvalidOperation, TypeError):
            raise ValueError(f'price_{code} "{value}" is not a number')
    return prices


class CategoryAdmin(MaimsModelAdmin):
    list_display = ('thumb', 'name', 'parent', 'product_count', 'show_on_homepage', 'homepage_order')
    list_display_links = ('thumb', 'name')
    list_filter = ('parent', 'show_on_homepage')
    list_editable = ('show_on_homepage', 'homepage_order')
    list_select_related = ('parent',)
    search_fields = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}
    autocomplete_fields = ('parent',)
    readonly_fields = ('image_preview',)
    fieldsets = (
        ('Basics', {
            'fields': ('name', 'slug', 'parent', 'description'),
            'description': 'Leave <b>parent</b> empty for a top-level category that can appear on the homepage.'}),
        ('Homepage showcase', {
            'fields': ('show_on_homepage', 'homepage_order', 'image', 'image_preview'),
            'description': 'Tick <b>show on homepage</b> to add this category to the "Shop by Category" strip. '
                           'Order 1 is shown first.'}),
    )

    @admin.display(description='Products')
    def product_count(self, obj):
        url = reverse('admin:products_product_changelist') + f'?category__id__exact={obj.pk}'
        return format_html('<a href="{}">{}</a>', url, obj.products.count())

    @admin.display(description='')
    def thumb(self, obj):
        return thumbnail(obj.get_image())

    @admin.display(description='Preview')
    def image_preview(self, obj):
        url = obj.get_image()
        if url:
            return mark_safe(f'<img src="{escape(url)}" style="max-width:320px;border-radius:12px;" />')
        return 'No image uploaded yet.'


class CollectionAdmin(MaimsModelAdmin):
    list_display = ('name', 'slug', 'is_active', 'product_count')
    list_display_links = ('name',)
    list_filter = ('is_active',)
    search_fields = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}

    @admin.display(description='Products')
    def product_count(self, obj):
        url = reverse('admin:products_product_changelist') + f'?collection__id__exact={obj.pk}'
        return format_html('<a href="{}">{}</a>', url, obj.products.count())


class HeroSlideAdmin(MaimsModelAdmin):
    list_display = ('thumb', 'title', 'order', 'is_active', 'button_text')
    list_display_links = ('thumb', 'title')
    list_editable = ('order', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('title', 'subtitle')
    readonly_fields = ('image_preview',)
    fieldsets = (
        ('Text on the slide', {'fields': ('title', 'subtitle', 'button_text', 'button_link')}),
        ('Background image', {
            'fields': ('image', 'external_image_url', 'image_preview'),
            'description': 'Upload an image OR paste an external https:// URL. The upload wins if both are set.'}),
        ('Position', {
            'fields': ('order', 'is_active'),
            'description': 'Order 1 shows first. Untick <b>active</b> to hide a slide without deleting it.'}),
    )

    @admin.display(description='')
    def thumb(self, obj):
        return thumbnail(obj.get_image_url(), width=96, height=48)

    @admin.display(description='Preview')
    def image_preview(self, obj):
        url = obj.get_image_url()
        if url:
            return mark_safe(f'<img src="{escape(url)}" style="max-width:520px;border-radius:12px;" />')
        return 'No image yet — upload one or paste an external URL.'


class SiteSettingsAdmin(MaimsModelAdmin):
    """One row controls every link and payment toggle — there is never more than one."""
    list_display = ('singleton_label', 'whatsapp_number', 'stripe_enabled', 'cod_enabled',
                    'whatsapp_enabled', 'updated_at')
    list_editable = ('stripe_enabled', 'cod_enabled', 'whatsapp_enabled')
    fieldsets = (
        ('Payments', {
            'fields': ('stripe_enabled', 'cod_enabled'),
            'description': 'Untick a method to hide it at checkout. Card payments also need a valid '
                           'STRIPE_SECRET_KEY in the environment.'}),
        ('WhatsApp Business', {
            'fields': ('whatsapp_enabled', 'whatsapp_number', 'whatsapp_greeting'),
            'description': 'Digits only with the country code, e.g. 351912345678. This powers the '
                           'Order-via-WhatsApp button and the floating chat bubble.'}),
        ('Facebook', {
            'fields': ('facebook_page_url', 'facebook_shop_url'),
            'description': 'Shown as header and footer buttons on the storefront.'}),
        ('Social links', {
            'fields': ('instagram_url', 'tiktok_url', 'twitter_url', 'youtube_url', 'linkedin_url'),
            'description': 'Leave a field blank to hide that button on the storefront.'}),
    )

    @admin.display(description='Settings')
    def singleton_label(self, obj):
        return 'Storefront links & payment methods'

    def has_add_permission(self, request):
        # Exactly one settings row may ever exist.
        return not SiteSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False

    def changelist_view(self, request, extra_context=None):
        """Skip the list page: send the operator straight to the single settings form."""
        if request.method == 'GET' and not request.GET.get('q'):
            row = SiteSettings.objects.first()
            if row:
                return HttpResponseRedirect(reverse('admin:products_sitesettings_change', args=[row.pk]))
        return super().changelist_view(request, extra_context)


# --- registration -------------------------------------------------------------------
# Registered as plain calls, not @decorators: Django 6's AdminSite.register()
# returns None, so it cannot be used as a class decorator.

maims_admin.register(Order, OrderAdmin)
maims_admin.register(Product, ProductAdmin)
maims_admin.register(Category, CategoryAdmin)
maims_admin.register(Collection, CollectionAdmin)
maims_admin.register(HeroSlide, HeroSlideAdmin)
maims_admin.register(SiteSettings, SiteSettingsAdmin)
