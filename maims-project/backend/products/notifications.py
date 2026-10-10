"""
Outbound notifications: order confirmation, fulfilment updates, admin alerts and
Facebook success stories.

Design rules, in priority order:

1. **A notification must never break a request.** Every send is wrapped, recorded
   and swallowed. If Meta is down while a customer is checking out, the order is
   still placed; the failure lands in OrderNotification for staff to retry.

2. **Exactly one message per event.** Order.last_notified_status records what the
   customer has already been told, so re-saving an order (the admin changelist
   saves every field at once, actions save again) cannot double-text a customer.

3. **Nothing is configured, nothing is attempted.** Each channel reports itself
   unconfigured and logs a `skipped` row rather than raising or silently doing
   nothing, so the admin can see what *would* have been sent.

Providers use the stdlib HTTP client so the project gains no new dependency.
"""

import json
import logging
import re
import urllib.error
import urllib.parse
import urllib.request
from decimal import Decimal

from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction
from django.utils import timezone

from .models import Order, OrderNotification, SiteSettings

logger = logging.getLogger(__name__)

GRAPH_VERSION = 'v21.0'
# E.164 allows at most 15 digits and a shortest sensible number is 7-8 digits.
MIN_PHONE_DIGITS = 8
MAX_PHONE_DIGITS = 15
HTTP_TIMEOUT = 10


# --- phone helpers -----------------------------------------------------------------

def normalize_phone(raw):
    """
    Turn whatever the customer typed into bare international digits.

    The checkout already collects a country code separately (`+351 912345678`), so
    this only strips formatting. A leading `00` international prefix is removed
    because WhatsApp's API wants `351912345678`, not `00351912345678`.
    """
    if not raw:
        return ''
    digits = re.sub(r'\D', '', str(raw))
    if digits.startswith('00'):
        digits = digits[2:]
    return digits


def is_plausible_whatsapp_number(digits):
    """
    Whether a number *could* be reachable on WhatsApp.

    There is no API that checks WhatsApp reachability without sending a message,
    so this is a shape check, not a lookup: the shop cannot be sure a number is on
    WhatsApp until it sends. It rejects the obviously wrong values that would
    otherwise burn an API call and get the sender template rejected.
    """
    return MIN_PHONE_DIGITS <= len(digits) <= MAX_PHONE_DIGITS


# --- low level helpers -------------------------------------------------------------

def _http_post_json(url, payload, headers, timeout=HTTP_TIMEOUT):
    """
    POST JSON and return (status_code, parsed_body).

    Raises on transport failure and on any 4xx/5xx so the caller records a real
    failure. urllib raises HTTPError for non-2xx, which is caught here only to
    read the response body (Meta puts the actual reason in it).
    """
    data = json.dumps(payload).encode('utf-8')
    request = urllib.request.Request(url, data=data, method='POST')
    request.add_header('Content-Type', 'application/json')
    for key, value in (headers or {}).items():
        request.add_header(key, value)

    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read().decode('utf-8', 'replace')
            return response.status, _safe_json(body)
    except urllib.error.HTTPError as exc:
        body = exc.read().decode('utf-8', 'replace')
        raise RuntimeError(f'HTTP {exc.code}: {_shorten(_safe_json(body))}') from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f'Network error: {exc.reason}') from exc


def _safe_json(text):
    try:
        return json.loads(text)
    except (TypeError, ValueError):
        return {'raw': (text or '')[:500]}


def _shorten(value, limit=300):
    """Provider errors can be long; keep the log and the admin table readable."""
    text = value if isinstance(value, str) else json.dumps(value)
    return text[:limit]


# --- message content ----------------------------------------------------------------

def money(amount, currency=''):
    symbols = {'EUR': '€', 'USD': '$', 'SEK': 'kr', 'BDT': '৳', 'PKR': 'Rs'}
    value = Decimal(amount or 0)
    return f"{symbols.get(currency, '')}{value:.2f} {currency}".strip()


def order_item_lines(order):
    return [
        f"{item.quantity} x {item.product.name}" + (f" ({item.size})" if item.size else '')
        for item in order.items.select_related('product').all()
    ]


def _store():
    return SiteSettings.get()


def admin_recipient_email():
    """Where the new-order alert goes: the admin setting, else the env fallback."""
    store = _store()
    return (store.notification_email or '').strip() or getattr(settings, 'ADMIN_RECEIVER_EMAIL', '')


def _template(store, template, order):
    """Fill the shop's editable success-story template."""
    names = [name for name in (line.split(' x ', 1)[-1].split(' (')[0] for line in order_item_lines(order))]
    values = {
        'order_id': str(order.pk),
        'first_name': order.first_name,
        'last_name': order.last_name,
        'place': order.place,
        'product_names': ', '.join(names) if names else 'your order',
        'currency': order.currency,
        'total': f'{order.total_amount:.2f}',
    }
    text = template or ''
    for key, value in values.items():
        text = text.replace('{' + key + '}', str(value))
    return text.strip()


# --- the customer-facing messages ----------------------------------------------------

def customer_subject(order):
    return f"[Maims] Order #{order.pk} — {order.status_message_label}"


def whatsapp_is_configured(store=None):
    """Whether the WhatsApp Cloud API credentials are present.

    Kept separate from the send so the notifier can tell "not set up" (a skip)
    apart from "set up but the send failed" (a real failure). Conflating the two
    would leave the admin's failed-notifications badge permanently red for a shop
    that simply has not connected WhatsApp yet.
    """
    store = store or _store()
    return bool(store.whatsapp_api_token and store.whatsapp_phone_number_id)


def facebook_is_configured(store=None):
    store = store or _store()
    return bool(store.facebook_page_id and store.facebook_page_access_token)


def customer_body(order):
    """One body used for both email and WhatsApp so the wording never diverges."""
    lines = [
        f"Hello {order.first_name},",
        "",
        f"Your Maims order #{order.pk} is now: {order.status_message_label}.",
        "",
    ]
    if order.status == 'rejected':
        lines.append("We are sorry — we are not able to take this order.")
        if order.rejection_reason:
            lines += ["", f"Reason: {order.rejection_reason}"]
        lines += ["", "Nothing has been charged. If this looks wrong, reply to this message."]
    elif order.status == 'accepted':
        lines.append("Good news — we have confirmed your order and will start packing it shortly.")
    elif order.status == 'packed':
        lines.append("Your order is packed and will be handed to the courier shortly.")
    elif order.status == 'shipped':
        lines.append("Your order is on its way!")
        if order.tracking_number:
            lines.append(f"Tracking number: {order.tracking_number}")
    elif order.status == 'delivered':
        lines.append("Your order has been delivered. We hope you love it!")
        review_hint = _first_product_url(order)
        if review_hint:
            lines += ["", f"Tell us how it went: {review_hint}"]
    elif order.status == 'cancelled':
        lines.append("Your order has been cancelled. If this was unexpected, please contact us.")
    else:  # 'new'
        lines.append("We have received your order and will confirm it shortly.")
        lines.append(f"Total: {money(order.total_amount, order.currency)}")

    lines += ["", "Your items:", *[f"  - {line}" for line in order_item_lines(order)]]
    lines += [
        "",
        f"Order total: {money(order.total_amount, order.currency)}",
        f"Delivering to: {order.address}, {order.zipcode} {order.place}",
        "",
        f"Questions? Reply to this message or email {settings.DEFAULT_FROM_EMAIL}.",
    ]
    return '\n'.join(lines)


def admin_new_order_body(order):
    admin_base = getattr(settings, 'BACKEND_BASE_URL', '').rstrip('/')
    lines = [
        f"New order #{order.pk}",
        "",
        f"Customer : {order.first_name} {order.last_name}",
        f"Email    : {order.email}",
        f"Phone    : {order.phone or '-'}",
        f"Address  : {order.address}, {order.zipcode} {order.place}",
        f"Payment  : {order.get_payment_method_display()}",
        f"Total    : {money(order.total_amount, order.currency)}",
        "",
        "Items:",
        *[f"  {line}" for line in order_item_lines(order)],
    ]
    if admin_base:
        lines += ["", f"Review it in the admin: {admin_base}/admin/products/order/{order.pk}/change/"]
    return '\n'.join(lines)


def _first_product_url(order):
    """Deep link to the first item's page, used to invite a review after delivery."""
    frontend = getattr(settings, 'FRONTEND_BASE_URL', '').rstrip('/')
    if not frontend:
        return ''
    item = order.items.select_related('product').first()
    return f"{frontend}/products/{item.product.slug}" if item else ''


# --- channel senders ------------------------------------------------------------------
# Each returns (ok, detail). They never raise: transport errors are converted to
# ok=False with a short reason so the caller can record the failure.

def _send_email(recipient, subject, body, from_email=None):
    try:
        send_mail(
            subject=subject,
            message=body,
            from_email=from_email or settings.DEFAULT_FROM_EMAIL or None,
            recipient_list=[recipient],
            fail_silently=False,
        )
        return True, ''
    except Exception as exc:
        logger.warning('Email to %s failed: %s', recipient, exc)
        return False, _shorten(str(exc))


def _send_whatsapp(to_digits, body, store=None):
    store = store or _store()
    if not store.whatsapp_api_token or not store.whatsapp_phone_number_id:
        return False, 'WhatsApp API not configured (missing token or Phone Number ID)'

    url = (f'https://graph.facebook.com/{GRAPH_VERSION}/{store.whatsapp_phone_number_id}/messages')
    payload = {
        'messaging_product': 'whatsapp',
        'recipient_type': 'individual',
        'to': to_digits,
        'type': 'text',
        'text': {'preview_url': False, 'body': body},
    }
    try:
        _http_post_json(url, payload, {'Authorization': f'Bearer {store.whatsapp_api_token}'})
        return True, ''
    except Exception as exc:
        logger.warning('WhatsApp send to %s failed: %s', to_digits, exc)
        return False, _shorten(str(exc))


def _post_facebook_story(text, store=None):
    store = store or _store()
    if not store.facebook_page_id or not store.facebook_page_access_token:
        return False, 'Facebook page not configured (missing Page ID or access token)'

    url = f'https://graph.facebook.com/{GRAPH_VERSION}/{store.facebook_page_id}/feed'
    # The token goes in the query string because that is what the Graph API
    # expects for a page feed post; the URL is never logged.
    separator = '&' if '?' in url else '?'
    url = f"{url}{separator}access_token={urllib.parse.quote(store.facebook_page_access_token)}"
    try:
        _http_post_json(url, {'message': text}, {})
        return True, ''
    except Exception as exc:
        logger.warning('Facebook post failed: %s', exc)
        return False, _shorten(str(exc))


# --- the recording layer ---------------------------------------------------------------

def _record(order, channel, audience, event, ok, recipient='', subject='', body='', error=''):
    """Persist the attempt. get_or_create-style dedupe lives in the callers."""
    return OrderNotification.objects.create(
        order=order,
        channel=channel,
        audience=audience,
        event=event,
        status='sent' if ok else 'failed',
        recipient=recipient,
        subject=subject,
        body=body,
        error=error,
        sent_at=timezone.now() if ok else None,
    )


def _already_sent(order, channel, audience, event):
    return OrderNotification.objects.filter(
        order=order, channel=channel, audience=audience, event=event, status='sent'
    ).exists()


def _record_skip(order, channel, audience, event, reason):
    logger.info('Notification skipped (order %s, %s/%s, %s): %s',
                order.pk, channel, audience, event, reason)
    return OrderNotification.objects.create(
        order=order, channel=channel, audience=audience, event=event,
        status='skipped', error=reason,
    )


# --- customer notifications --------------------------------------------------------------

def notify_customer(order, event=None):
    """
    Tell the customer about `order` — by email, and over WhatsApp if they opted in.

    Safe to call more than once for the same event: a successful send short-circuits
    the rest, so a duplicate save cannot double-text anybody.
    """
    event = event or order.status
    store = _store()

    if not store.customer_notifications_enabled:
        return _record_skip(order, 'email', 'customer', event,
                            'Customer notifications are disabled in Store settings')

    subject = customer_subject(order)
    body = customer_body(order)

    # --- email
    if order.email and not _already_sent(order, 'email', 'customer', event):
        ok, error = _send_email(order.email, subject, body)
        _record(order, 'email', 'customer', event, ok, order.email, subject, body, error)
    elif not order.email:
        _record_skip(order, 'email', 'customer', event, 'No email address on the order')

    # --- WhatsApp
    if not _already_sent(order, 'whatsapp', 'customer', event):
        digits = normalize_phone(order.phone)
        if not order.whatsapp_opt_in:
            _record_skip(order, 'whatsapp', 'customer', event,
                         'Customer did not opt in to WhatsApp updates')
        elif not store.customer_whatsapp_notifications:
            _record_skip(order, 'whatsapp', 'customer', event,
                         'WhatsApp notifications disabled in Store settings')
        elif not digits:
            _record_skip(order, 'whatsapp', 'customer', event, 'No phone number on the order')
        elif not is_plausible_whatsapp_number(digits):
            # Recorded rather than silently dropped so the shop can see that some
            # customers typed a number WhatsApp will not accept.
            _record_skip(order, 'whatsapp', 'customer', event,
                         f'"{digits}" is not an international phone number WhatsApp can use')
        elif not whatsapp_is_configured(store):
            # Not set up yet. A skip, not a failure — otherwise the admin's
            # "failed notifications" alert would be permanently red for a shop
            # that has simply not connected WhatsApp.
            _record_skip(order, 'whatsapp', 'customer', event,
                         'WhatsApp API not configured in Store settings')
        else:
            ok, error = _send_whatsapp(digits, body, store)
            _record(order, 'whatsapp', 'customer', event, ok, digits, subject, body, error)


# --- admin alerts --------------------------------------------------------------------------

def notify_admin_new_order(order):
    """The 'we have a new order' alert: email plus WhatsApp if a number is configured."""
    if order.last_notified_status == 'new':
        return  # already alerted for this status

    store = _store()
    subject = f"[Maims] New order #{order.pk} — {money(order.total_amount, order.currency)}"
    body = admin_new_order_body(order)

    recipient = admin_recipient_email()
    if recipient and not _already_sent(order, 'email', 'admin', 'new'):
        ok, error = _send_email(recipient, subject, body)
        _record(order, 'email', 'admin', 'new', ok, recipient, subject, body, error)
    else:
        _record_skip(order, 'email', 'admin', 'new',
                     'No notification address configured' if not recipient
                     else 'Already notified')

    digits = normalize_phone(store.admin_whatsapp_number)
    if not digits or not is_plausible_whatsapp_number(digits):
        _record_skip(order, 'whatsapp', 'admin', 'new',
                     'No admin WhatsApp number configured in Store settings')
    elif not whatsapp_is_configured(store):
        _record_skip(order, 'whatsapp', 'admin', 'new',
                     'WhatsApp API not configured in Store settings')
    elif not _already_sent(order, 'whatsapp', 'admin', 'new'):
        ok, error = _send_whatsapp(digits, body, store)
        _record(order, 'whatsapp', 'admin', 'new', ok, digits, subject, body, error)


# --- Facebook success story -----------------------------------------------------------------

def post_success_story(order):
    """
    Publish the "another happy customer" post once an order is delivered.

    Deliberately NOT gated on `last_notified_status`: that field tracks customer
    messages. Delivery itself is the only trigger, and the dedupe is a successful
    facebook/delivered row so a re-delivered or re-saved order cannot post twice.
    """
    store = _store()
    if not store.facebook_post_on_delivery:
        return _record_skip(order, 'facebook', 'customer', 'delivered',
                            'Facebook success stories disabled in Store settings')
    if _already_sent(order, 'facebook', 'customer', 'delivered'):
        return
    if not facebook_is_configured(store):
        return _record_skip(order, 'facebook', 'customer', 'delivered',
                            'Facebook page not configured in Store settings')

    text = _template(store, store.facebook_success_story_template, order)
    if not text:
        return _record_skip(order, 'facebook', 'customer', 'delivered',
                            'Success story template is empty')

    ok, error = _post_facebook_story(text, store)
    _record(order, 'facebook', 'customer', 'delivered', ok, store.facebook_page_id or '', '', text, error)


# --- the entry point wired to order changes ---------------------------------------------------

def handle_order_status_change(order, previous_status=None):
    """
    React to an order moving between states.

    Called from the post_save signal so every write path is covered: the admin
    change form, the one-click advance button, list_editable on the changelist,
    bulk actions and any future API.

    `Order.last_notified_status` is the idempotency guard. It is compared and then
    written with a queryset update (not instance.save) so the write cannot re-fire
    the signal that is currently executing.
    """
    if order.status == order.last_notified_status:
        return

    previous_status = previous_status or order.last_notified_status
    changed = previous_status != order.status

    try:
        if order.status == 'new':
            # The alert about the order existing at all.
            notify_admin_new_order(order)
        elif order.should_notify_customer:
            notify_customer(order)
        elif order.status == 'delivered':
            # Notified above via NOTIFY_STATUSES; nothing extra for the customer.
            pass

        if order.status == 'delivered':
            post_success_story(order)

        # Mark as told before releasing, so a crash mid-send cannot cause a
        # resend storm on the next save.
        Order.objects.filter(pk=order.pk).update(last_notified_status=order.status)
    except Exception:
        # Belt and braces: the signal must never propagate into a checkout or an
        # admin save.
        logger.exception('Notification dispatch failed for order %s', order.pk)


def dispatch_for_order(order_id):
    """
    Queue notifications for an order from outside a request.

    Sends happen after the surrounding transaction commits: a "your order is
    confirmed" mail for an order that then rolls back is worse than no mail.
    """
    transaction.on_commit(lambda: handle_order_status_change(_reload(order_id)))


def _reload(order_id):
    """Fetch a fresh order (and its lines) by id."""
    return Order.objects.get(pk=order_id)


def resend_failed(order, channel=None):
    """
    Retry the failed sends for an order, from the admin.

    Failed rows are deleted first so the dedupe check (which only looks at
    successful sends) does not short-circuit the retry.
    """
    failed = order.notifications.filter(status='failed')
    if channel:
        failed = failed.filter(channel=channel)
    channels = list(failed.values_list('channel', 'audience').distinct())
    failed.delete()

    for ch, audience in channels:
        Order.objects.filter(pk=order.pk).update(last_notified_status='')
        fresh = Order.objects.get(pk=order.pk)
        if audience == 'admin':
            notify_admin_new_order(fresh)
        else:
            notify_customer(fresh)