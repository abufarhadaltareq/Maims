"""Admin registrations that belong to the project rather than the shop models.

The default auth User page is replaced with one built around the question the shop
actually asks about a customer: what have they ordered, what have they spent, and
how do I reach them.
"""
from django.conf import settings
from django.contrib import admin
from django.contrib.auth.admin import GroupAdmin, UserAdmin
from django.contrib.auth.models import Group, User
from django.db.models import Count, Prefetch
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from urllib.parse import quote

from unfold.admin import ModelAdmin as UnfoldModelAdmin
from unfold.admin import StackedInline as UnfoldStackedInline
from unfold.admin import TabularInline as UnfoldTabularInline

from products.admin import CURRENCY_SYMBOLS
from products.models import Order, OrderNotification, Review, UserProfile

from .admin_site import maims_admin


# --- Unfold dashboard / navigation callbacks ---------------------------------------
# Wired up via UNFOLD in core/settings.py. Kept here (rather than in admin_site.py)
# because they read the shop models and are part of the admin's presentation.

# The order queues, in the order they must be worked through. 'new' comes first
# because it is the only queue that blocks on a decision: staff must accept or
# decline before anything else happens to the order.
QUEUES = (
    ('new', 'Awaiting our decision', 'status__exact=new'),
    ('accepted', 'Accepted, to pack', 'status__exact=accepted'),
    ('packed', 'Packed, waiting for the courier', 'status__exact=packed'),
    ('shipped', 'Out for delivery', 'status__exact=shipped'),
    ('delivered', 'Delivered', 'status__exact=delivered'),
    ('rejected', 'Declined', 'status__exact=rejected'),
    ('cancelled', 'Cancelled or returned', 'status__exact=cancelled'),
)


def dashboard_callback(request, context):
    """Numbers on the admin home page (UNFOLD["DASHBOARD_CALLBACK"]).

    Unfold renders templates/admin/index.html with this context, so the dashboard
    template reads ``orders_today``, ``open_orders``, ``queues``, ``pending_notifications``
    and ``unanswered_reviews``.
    """
    today = timezone.localdate()
    open_statuses = ('new', 'accepted', 'packed', 'shipped')
    orders_url = reverse('admin:products_order_changelist')
    context.update({
        'orders_today': Order.objects.filter(created_at__date=today).count(),
        'open_orders': Order.objects.filter(status__in=open_statuses).count(),
        # The number that actually needs a human decision right now.
        'awaiting_decision': Order.objects.filter(status='new').count(),
        # Sends that did not get through. Surfaced because a silently failed
        # WhatsApp means a customer never hears about their delivery.
        'pending_notifications': OrderNotification.objects.filter(status='failed').count(),
        # Reviews waiting to be looked at, if any are hidden.
        'unanswered_reviews': Review.objects.filter(is_approved=False).count(),
        'queues': [
            {
                'label': label,
                'count': Order.objects.filter(status=status).count(),
                'url': f'{orders_url}?{query}',
            }
            for status, label, query in QUEUES
        ],
    })
    return context


def environment_callback(request):
    """Header label so it is obvious which environment the admin is running in."""
    if settings.DEBUG:
        return ['Development', 'warning']
    return ['Live', 'success']


def new_orders_badge(request):
    """Sidebar badge: orders still waiting for the shop to accept or decline."""
    return Order.objects.filter(status='new').count()


def failed_notifications_badge(request):
    """Sidebar badge: messages that did not get through.

    A silently failed email or WhatsApp means a customer never hears about their
    delivery, so this is shown next to the orders rather than buried.
    """
    return OrderNotification.objects.filter(status='failed').count()


class UserProfileInline(UnfoldStackedInline):
    """Delivery details the customer filled in on the storefront."""
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'Storefront profile'
    fields = ('phone', 'address', 'zipcode', 'place')


class OrderInline(UnfoldTabularInline):
    """Recent orders placed by this customer, newest first."""
    model = Order
    extra = 0
    can_delete = False
    show_change_link = True
    fields = ('id', 'created_at', 'total', 'status', 'is_paid')
    readonly_fields = fields
    ordering = ('-created_at',)

    def has_add_permission(self, request, obj=None):
        return False

    @admin.display(description='Total')
    def total(self, obj):
        symbol = CURRENCY_SYMBOLS.get(obj.currency, '')
        return f"{symbol}{obj.total_amount} {obj.currency}"

    @admin.display(description='Payment')
    def is_paid(self, obj):
        return 'Paid' if obj.is_paid else 'Unpaid'


# UserAdmin supplies the creation form (password1/password2) and add_fieldsets
# handling; UnfoldModelAdmin supplies the Tailwind shell and the Add link.
class MaimsUserAdmin(UserAdmin, UnfoldModelAdmin):
    change_form_template = 'admin/maims_user_change_form.html'
    list_display = ('username', 'email', 'full_name', 'order_count', 'spent', 'place', 'is_staff')
    list_filter = ('is_staff', 'is_superuser', 'is_active')
    search_fields = ('username', 'email', 'first_name', 'last_name', 'profile__phone',
                     'profile__place')
    list_select_related = ('profile',)
    ordering = ('-date_joined',)
    inlines = (UserProfileInline, OrderInline)
    save_on_top = True
    actions_on_top = True
    fieldsets = (
        ('Account', {'fields': ('username', 'password')}),
        ('Personal info', {'fields': ('first_name', 'last_name', 'email')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser',
                                    'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )
    readonly_fields = ('last_login', 'date_joined')
    add_fieldsets = (
        (None, {'classes': ('wide',), 'fields': ('username', 'password1', 'password2')}),
    )

    def get_queryset(self, request):
        # Paid orders are prefetched once for the whole page so the lifetime-value
        # column costs one query instead of one per customer.
        return super().get_queryset(request).select_related('profile').annotate(
            order_total=Count('orders', distinct=True),
        ).prefetch_related(
            Prefetch('orders', queryset=Order.objects.filter(is_paid=True).only('user_id', 'currency', 'total_amount')),
        )

    @admin.display(description='Name', ordering='first_name')
    def full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}".strip() or '—'

    @admin.display(description='Orders', ordering='order_total')
    def order_count(self, obj):
        count = getattr(obj, 'order_total', 0) or 0
        if not count:
            return '—'
        url = reverse('admin:products_order_changelist') + f'?user__id__exact={obj.pk}'
        return format_html('<a href="{}"><strong>{}</strong></a>', url, count)

    @admin.display(description='Lifetime value')
    def spent(self, obj):
        """Total paid spend, shown per currency so amounts are never added together."""
        totals = {}
        for order in obj.orders.all():
            totals[order.currency] = totals.get(order.currency, 0) + order.total_amount
        if not totals:
            return '—'
        return mark_safe(', '.join(
            format_html('{}', f"{CURRENCY_SYMBOLS.get(code, '')}{amount} {code}")
            for code, amount in sorted(totals.items())
        ))

    @admin.display(description='Location')
    def place(self, obj):
        profile = getattr(obj, 'profile', None)
        return profile.place if profile else '—'

    def change_view(self, request, object_id, form_url='', extra_context=None):
        """Add one-click contact links to the customer page."""
        extra_context = extra_context or {}
        user = self.get_object(request, object_id)
        if user is not None and self.has_view_permission(request):
            profile = getattr(user, 'profile', None)
            phone = profile.phone if profile else ''
            message = f"Hello {user.first_name or user.username}, this is Maims."
            extra_context['customer_contact'] = {
                'phone': phone,
                'whatsapp': f"https://wa.me/{''.join(c for c in phone if c.isdigit())}?text={quote(message)}"
                            if phone else '',
                'email': user.email,
            }
        return super().change_view(request, object_id, form_url, extra_context)


# `core` is listed after `django.contrib.auth` in INSTALLED_APPS, so the default
# User admin is registered on the default site; we register our own version on the
# Maims site, which is the one core.urls exposes.
class MaimsGroupAdmin(GroupAdmin, UnfoldModelAdmin):
    """Django's Group admin (filter_horizontal for permissions) with Unfold styling."""


maims_admin.register(User, MaimsUserAdmin)
maims_admin.register(Group, MaimsGroupAdmin)
