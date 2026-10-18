"""Facebook Page product synchronization.

Two entry points drive this module:

1. The webhook endpoint (``products/views.facebook_webhook``) — Meta
   pushes ``feed`` changes (post added / edited / removed) here in
   near-real time.
2. The reconciliation command (``manage.py sync_facebook_catalog``) —
   a cron job that re-reads the last N posts and fixes anything the
   webhook missed (e.g. while the app was deploying).

Everything here is deliberately defensive: a malformed post, an
expired Facebook image URL or an unreachable Cloudinary must never
raise into the caller. The webhook answers 200 and logs; the
command reports per-post results and keeps going.
"""

import hashlib
import hmac
import logging
import re
import time
from decimal import Decimal, InvalidOperation
from urllib.parse import urlparse

import requests
from django.conf import settings
from django.core.files.base import ContentFile
from django.utils.text import slugify

from .models import Category, CurrencyPrice, Product, SiteSettings

logger = logging.getLogger(__name__)

# Meta Graph API version pinned so a silent API upgrade cannot
# change the shape of `feed` payloads underneath us.
GRAPH_API_BASE = 'https://graph.facebook.com/v21.0'

# Currency symbol -> CurrencyPrice code. `rs` covers Pakistani
# rupees; `৳` is BDT. A "price: 2500" line with no symbol falls
# back to FACEBOOK_SYNC_DEFAULT_CURRENCY.
CURRENCY_SYMBOLS = {
    '€': 'EUR',
    '৳': 'BDT',
    '$': 'USD',
    'kr': 'SEK',
    'rs': 'PKR',
}

# "€ 120.00", "৳1,200", "$49.99", "Rs. 1500", "kr 299".
# The amount allows mixed separators so "1.200,50" and
# "1,200.50" are both captured whole (normalized in _to_decimal).
PRICE_RE = re.compile(
    r'(?P<symbol>€|৳|\$|kr|Rs\.?)\s*(?P<amount>\d(?:[\d.,]*\d)?)',
    re.IGNORECASE,
)
# "price: 2500" / "Price 2500" with no currency symbol.
LABELED_PRICE_RE = re.compile(
    r'\bprice\s*[:：]?\s*(\d(?:[\d.,]*\d)?)',
    re.IGNORECASE,
)
# English + Bengali sold markers — the page posts in both.
SOLD_OUT_RE = re.compile(r'\b(sold\s*out|soldout|sold|বিক্রিত)\b', re.IGNORECASE)


# --- configuration -------------------------------------------------------------

def get_page_credentials():
    """(page_id, access_token) for the Graph API.

    Environment variables win; otherwise the admin-editable
    SiteSettings row (Admin → Store settings) is used, so the shop
    can be configured from either place without a code deploy.
    """
    try:
        site = SiteSettings.get()
    except Exception:
        site = None
    page_id = settings.FACEBOOK_PAGE_ID or (site.facebook_page_id if site else '') or ''
    token = settings.FACEBOOK_PAGE_ACCESS_TOKEN or (site.facebook_page_access_token if site else '') or ''
    return page_id.strip(), token.strip()


# --- post parsing --------------------------------------------------------------

def _to_decimal(raw):
    """Tolerant number parse: handles "1,200.50", "1.200,50" and
    plain "1200" (the rightmost separator is the decimal point)."""
    text = (raw or '').strip()
    if not text:
        return None
    try:
        if ',' in text and '.' in text:
            if text.rfind(',') > text.rfind('.'):
                text = text.replace('.', '').replace(',', '.')
            else:
                text = text.replace(',', '')
        elif ',' in text:
            # Decimal comma ("1,20") only when the comma is followed
            # by exactly two digits at the end; otherwise it is a
            # thousands separator ("1,200").
            if re.fullmatch(r'\d+,\d{2}', text):
                text = text.replace(',', '.')
            else:
                text = text.replace(',', '')
        return Decimal(text)
    except (InvalidOperation, ValueError):
        return None


def parse_product_post(message):
    """Best-effort parse of a Facebook post into product fields.

    Expected (tolerant) layout — first line is the title, a line
    with a currency amount is the price, the rest is the description:

        Jamdani Saree — Lotus
        € 120.00
        Handwoven in Dhaka, 6 yards, includes blouse piece

    Returns a dict with title, description, price (Decimal or None),
    currency and sold_out. Never raises.
    """
    result = {'title': '', 'description': '', 'price': None,
              'currency': settings.FACEBOOK_SYNC_DEFAULT_CURRENCY,
              'sold_out': False}
    try:
        lines = [ln.strip() for ln in (message or '').splitlines()]
        lines = [ln for ln in lines if ln]
        if not lines:
            return result

        # A sold-out marker anywhere in the post wins over stock defaults.
        if SOLD_OUT_RE.search(message or ''):
            result['sold_out'] = True

        # Title = first line, minus leading bullets/dashes. A price
        # written on the same line ("Kurta €120") is extracted and
        # removed from the title.
        title = re.sub(r'^[\s•·*#\-—–]+', '', lines[0]).strip()
        title_price = PRICE_RE.search(title)
        if title_price:
            result['price'] = _to_decimal(title_price.group('amount'))
            result['currency'] = CURRENCY_SYMBOLS.get(
                title_price.group('symbol').lower().rstrip('.'),
                settings.FACEBOOK_SYNC_DEFAULT_CURRENCY)
            title = title[:title_price.start()].strip(' -—–|·•*')
        result['title'] = title[:255]

        description_lines = []
        for ln in lines[1:]:
            if result['price'] is None:
                price_match = PRICE_RE.search(ln)
                if price_match:
                    result['price'] = _to_decimal(price_match.group('amount'))
                    result['currency'] = CURRENCY_SYMBOLS.get(
                        price_match.group('symbol').lower().rstrip('.'),
                        settings.FACEBOOK_SYNC_DEFAULT_CURRENCY)
                    continue  # the price line is not description
                labeled = LABELED_PRICE_RE.search(ln)
                if labeled:
                    result['price'] = _to_decimal(labeled.group(1))
                    continue
            description_lines.append(ln)
        result['description'] = '\n'.join(description_lines)[:2000]
    except Exception:
        logger.exception('Failed to parse Facebook post')
    return result


def unique_slug(base, exclude_id=None):
    """`base`, `base-2`, `base-3`… never colliding with an existing
    product slug. Product.slug is unique and the storefront resolves
    products with .get(slug=...), so a collision is a 500."""
    base = (slugify(base) or 'facebook-product')[:60]
    slug = base
    suffix = 2
    while True:
        qs = Product.objects.filter(slug=slug)
        if exclude_id:
            qs = qs.exclude(id=exclude_id)
        if not qs.exists():
            return slug
        slug = f"{base}-{suffix}"
        suffix += 1


def get_sync_category():
    """The category Facebook-synced products land in, created on
    first use (Product.category is a required FK)."""
    slug = settings.FACEBOOK_SYNC_CATEGORY_SLUG or 'facebook-sync'
    category, _ = Category.objects.get_or_create(
        slug=slug,
        defaults={'name': slug.replace('-', ' ').title()},
    )
    return category


# --- image pipeline ------------------------------------------------------------

def _image_format(data):
    """'jpg'/'png'/'gif'/'webp' from the magic bytes, or None."""
    if data[:8] == b'\x89PNG\r\n\x1a\n':
        return 'png'
    if data[:3] == b'\xff\xd8\xff':
        return 'jpg'
    if data[:6] in (b'GIF87a', b'GIF89a'):
        return 'gif'
    if data[:4] == b'RIFF' and data[8:12] == b'WEBP':
        return 'webp'
    return None


def download_image(url, timeout=15):
    """Fetch the Facebook `full_picture` bytes, or None on any
    failure (expired URL, timeout, non-image, >10MB)."""
    try:
        response = requests.get(url, timeout=timeout,
                                headers={'User-Agent': 'Maims-Store/1.0'})
        response.raise_for_status()
        if len(response.content) > 10 * 1024 * 1024:
            logger.warning('Facebook image too large (%s bytes), skipping',
                           len(response.content))
            return None
        return response.content
    except Exception:
        logger.warning('Could not download Facebook image %s', url, exc_info=True)
        return None


def _cloudinary_credentials():
    """Parse CLOUDINARY_URL (cloudinary://API_KEY:API_SECRET@CLOUD_NAME)
    into (api_key, api_secret, cloud_name), or (None, None, None)."""
    url = (settings.CLOUDINARY_URL or '').strip()
    if not url:
        return None, None, None
    parsed = urlparse(url)
    netloc = parsed.netloc or parsed.path  # tolerate a missing scheme
    if '@' in netloc:
        auth, cloud_name = netloc.rsplit('@', 1)
    else:
        auth, cloud_name = '', netloc
    api_key, _, api_secret = auth.partition(':')
    return api_key or None, api_secret or None, cloud_name or None


def _cloudinary_signature(params, api_secret):
    """Cloudinary's signed-request algorithm: sha1 over the
    alphabetically sorted "k=v" pairs joined by '&', plus the secret."""
    payload = '&'.join(f'{k}={params[k]}' for k in sorted(params) if params[k] not in (None, ''))
    return hashlib.sha1(f'{payload}{api_secret}'.encode('utf-8')).hexdigest()


def upload_to_cloudinary(source_url, public_id):
    """Re-host a Facebook image on Cloudinary; return the secure URL
    or None.

    Upload-by-URL: Cloudinary fetches `source_url` server-side, so
    the photo lands on our CDN and never expires with Meta's
    lookaside URLs. `overwrite` lets an edited post replace its
    earlier photo under the same public_id.
    """
    api_key, api_secret, cloud_name = _cloudinary_credentials()
    if not (api_key and api_secret and cloud_name):
        return None
    params = {'file': source_url, 'public_id': public_id, 'overwrite': True}
    params['timestamp'] = str(int(time.time()))
    params['signature'] = _cloudinary_signature(params, api_secret)
    params['api_key'] = api_key
    try:
        response = requests.post(
            f'https://api.cloudinary.com/v1_1/{cloud_name}/image/upload',
            data=params, timeout=30)
        response.raise_for_status()
        return response.json().get('secure_url')
    except Exception:
        logger.warning('Cloudinary upload failed for %s', public_id, exc_info=True)
        return None


def attach_product_image(product, picture_url, post_id):
    """Re-host the Facebook photo for a product. Preference order:

    1. Cloudinary (never expires, served from CDN) — Cloudinary
       fetches the Facebook URL itself.
    2. Django's default storage (local disk today, S3-swappable via
       the STORAGES setting) — the photo is downloaded first.

    Failure of both is logged and skipped: the product still syncs,
    just without a photo.
    """
    if not picture_url:
        return
    cloud_url = upload_to_cloudinary(picture_url, f'maims/fb/{post_id}')
    if cloud_url:
        product.facebook_image_url = cloud_url
        product.save(update_fields=['facebook_image_url'])
        return
    data = download_image(picture_url)
    if not data:
        return
    fmt = _image_format(data) or 'jpg'
    name = f'uploads/facebook/fb_{post_id}_{int(time.time())}.{fmt}'
    try:
        product.image.save(name, ContentFile(data), save=True)
    except Exception:
        logger.warning('Could not store Facebook image for post %s', post_id, exc_info=True)


# --- Graph API -----------------------------------------------------------------

def fetch_post(post_id):
    """Full post payload (message + full_picture) for one post id."""
    _, token = get_page_credentials()
    if not token:
        return None
    try:
        response = requests.get(
            f'{GRAPH_API_BASE}/{post_id}',
            params={'fields': 'id,message,full_picture,created_time,updated_time',
                    'access_token': token},
            timeout=15)
        response.raise_for_status()
        return response.json()
    except Exception:
        logger.warning('Graph API fetch failed for post %s', post_id, exc_info=True)
        return None


def fetch_page_feed(limit=50):
    """The page's most recent posts via `/{page-id}/feed`."""
    page_id, token = get_page_credentials()
    if not page_id or not token:
        return []
    try:
        response = requests.get(
            f'{GRAPH_API_BASE}/{page_id}/feed',
            params={'fields': 'id,message,full_picture,created_time,updated_time',
                    'limit': limit, 'access_token': token},
            timeout=20)
        response.raise_for_status()
        return response.json().get('data') or []
    except Exception:
        logger.warning('Graph API feed fetch failed', exc_info=True)
        return []


# --- product upsert --------------------------------------------------------------

def upsert_product_from_post(post_id, message, picture_url=''):
    """Create or update the Product for one Facebook post. Matched
    idempotently on facebook_post_id, so a retried webhook or a
    re-run of the sync command can never duplicate a product."""
    parsed = parse_product_post(message)
    title = parsed['title']
    if not title:
        logger.info('Facebook post %s has no parseable title; skipped', post_id)
        return None

    category = get_sync_category()
    product = Product.objects.filter(facebook_post_id=post_id).first()

    if product is None:
        product = Product.objects.create(
            category=category,
            facebook_post_id=post_id,
            name=title,
            slug=unique_slug(title),
            description=parsed['description'],
            stock=0 if parsed['sold_out'] else settings.FACEBOOK_SYNC_DEFAULT_STOCK,
        )
        action = 'created'
    else:
        updates = {
            'name': title,
            'description': parsed['description'],
            'slug': unique_slug(title, exclude_id=product.id),
        }
        if parsed['sold_out']:
            updates['stock'] = 0
        for key, value in updates.items():
            setattr(product, key, value)
        product.save(update_fields=list(updates))
        action = 'updated'

    if parsed['price'] is not None:
        CurrencyPrice.objects.update_or_create(
            product=product, currency=parsed['currency'],
            defaults={'price': parsed['price']})

    if picture_url:
        attach_product_image(product, picture_url, post_id)

    logger.info('Facebook post %s %s as product #%s', post_id, action, product.id)
    return product


def mark_product_sold(post_id):
    """A deleted post means the item is gone from the shop: stock 0.

    The Product row is never deleted here — Product is an OrderItem
    FK target (CASCADE), so deleting it would destroy order history.
    """
    updated = Product.objects.filter(facebook_post_id=post_id).update(stock=0)
    if updated:
        logger.info('Facebook post %s removed; product marked sold', post_id)
        return 'marked sold'
    return 'no product linked'


def handle_feed_change(value):
    """Apply one `feed` change value from a webhook payload.
    Returns a short status string for the webhook response."""
    post_id = (value.get('post_id') or '').strip()
    verb = (value.get('verb') or '').strip().lower()
    if not post_id:
        return 'ignored: no post_id'

    if verb == 'removed':
        return mark_product_sold(post_id)

    # `added` / `edited` — the webhook value often carries only the
    # id, so re-fetch the full post from the Graph API when needed.
    message = value.get('message') or ''
    picture = value.get('full_picture') or value.get('picture') or ''
    if not message or not picture:
        fetched = fetch_post(post_id)
        if fetched:
            message = fetched.get('message') or message
            picture = fetched.get('full_picture') or picture
    if not message:
        return 'ignored: post has no text'
    upsert_product_from_post(post_id, message, picture)
    return 'upserted'


# --- webhook verification --------------------------------------------------------

def verify_webhook_request(query):
    """Meta's URL verification: `hub.mode=subscribe` plus the
    verify token must match; return the hub.challenge to echo, or
    None when verification fails."""
    mode = query.get('hub.mode', '')
    token = query.get('hub.verify_token', '')
    challenge = query.get('hub.challenge', '')
    expected = settings.FACEBOOK_WEBHOOK_VERIFY_TOKEN
    if mode == 'subscribe' and challenge and expected and \
            hmac.compare_digest(token, expected):
        return challenge
    return None


def verify_signature(body, signature_header):
    """Meta signs webhook bodies with X-Hub-Signature-256
    (HMAC-SHA256 of the body using the app secret).

    True when the signature matches — or when no FACEBOOK_APP_SECRET
    is configured (verification is then advisory: the verify token
    already gates who can register the endpoint, and rejecting
    everything would break the sync for operators who skip the
    optional secret). A warning is logged so the gap is visible.

    In production (DEBUG=False) we enforce signature verification:
    if FACEBOOK_APP_SECRET is not set, reject all requests. In debug,
    we log a warning and accept any payload for development convenience.
    """
    secret = settings.FACEBOOK_APP_SECRET
    if not secret:
        if not settings.DEBUG:
            logger.warning('FACEBOOK_APP_SECRET is not set in production; rejecting all webhook requests.')
            return False
        else:
            logger.warning('FACEBOOK_APP_SECRET is not set; Facebook webhook payloads are accepted without signature verification (DEBUG=True).')
            return True
    if not signature_header:
        return False
    expected = 'sha256=' + hmac.new(
        secret.encode('utf-8'), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature_header)
