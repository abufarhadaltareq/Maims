"""Custom admin site for Maims.

The home page is deliberately plain. It shows three things and nothing else:
what arrived today, which order queue needs working on, and where to edit the data
that the storefront displays. Everything else is a click away from the model list.
"""
from django.contrib import admin
from django.urls import reverse
from django.utils import timezone

ORDERS = 'products_order_changelist'
PRODUCTS = 'products_product_changelist'

# The order queues, in the order they must be worked through.
QUEUES = (
    ('new', 'Waiting to be packed', 'status__exact=new'),
    ('packed', 'Packed, waiting for the courier', 'status__exact=packed'),
    ('shipped', 'Out for delivery', 'status__exact=shipped'),
    ('delivered', 'Delivered', 'status__exact=delivered'),
    ('cancelled', 'Cancelled or returned', 'status__exact=cancelled'),
)


class MaimsAdminSite(admin.AdminSite):
    site_header = 'Maims Store Admin'
    site_title = 'Maims Admin'
    index_title = 'Maims Store'
    enable_nav_sidebar = True

    # No `class Media` here on purpose: jazzmin's admin/base.html does not render
    # {{ media }}, so the Maims stylesheet is injected once by the project's
    # templates/admin/base_site.html instead. Declaring it in both places would
    # load it twice on every page.

    def each_context(self, request):
        context = super().each_context(request)
        context['maims_brand'] = 'Maims'
        return context

    def index(self, request, extra_context=None):
        from products.models import Order

        extra_context = extra_context or {}
        today = timezone.localdate()
        open_statuses = ('new', 'packed', 'shipped')
        orders_url = reverse(f'admin:{ORDERS}')

        extra_context.update({
            'orders_today': Order.objects.filter(created_at__date=today).count(),
            'open_orders': Order.objects.filter(status__in=open_statuses).count(),
            'queues': [
                {
                    'label': label,
                    'count': Order.objects.filter(status=status).count(),
                    'url': f'{orders_url}?{query}',
                }
                for status, label, query in QUEUES
            ],
        })
        return super().index(request, extra_context)


maims_admin = MaimsAdminSite(name='admin')
