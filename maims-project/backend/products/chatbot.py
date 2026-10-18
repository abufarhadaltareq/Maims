"""
Maims AI Shopping Assistant & Stylist Agent.

Provides a multi-tier AI agent for the Maims luxury fashion store:
1. LLM-Powered Mode: Connects to OpenAI / Groq / Anthropic / OpenRouter via OpenAI-compatible
   endpoint if an API key (OPENAI_API_KEY / LLM_API_KEY) is configured.
   Executes real-time tool calling against the Django ORM (product search, order tracking,
   policies, WhatsApp concierge).
2. Built-in E-Commerce Agent Engine: If no API key is set (or during network/service degradation),
   an intelligent domain-specific NLU agent takes over seamlessly. It performs multi-turn intent
   classification, semantic & keyword product filtering, order tracking, sizing guidance, and
   policy consultation with zero external API dependencies.
"""

import json
import logging
import os
import re
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, List, Optional, Tuple

import requests
from django.conf import settings
from django.core.cache import cache
from django.db.models import Avg, Count, Prefetch, Q

from .models import Category, CurrencyPrice, Order, OrderItem, Product, SiteSettings

logger = logging.getLogger(__name__)

CURRENCY_SYMBOLS = {
    'EUR': '€',
    'USD': '$',
    'PKR': 'Rs',
    'SEK': 'kr',
    'BDT': '৳',
}

RATE_TO_USD = {
    'SEK': 0.095,
    'PKR': 0.0036,
    'EUR': 1.08,
    'BDT': 0.0085,
    'USD': 1.0,
}


def format_price(amount: Optional[Decimal], currency: str = 'EUR') -> str:
    """Format price with appropriate currency symbol and locale styling."""
    curr = (currency or 'EUR').upper()
    sym = CURRENCY_SYMBOLS.get(curr, curr)
    if amount is None:
        return f"{sym} 0.00" if curr != 'SEK' else f"0.00 {sym}"

    try:
        val = float(amount)
    except (TypeError, ValueError):
        return f"{sym} 0.00"

    if curr in ('PKR', 'BDT'):
        return f"{sym} {int(round(val)):,}"
    elif curr == 'SEK':
        return f"{val:.2f} {sym}"
    elif curr in ('EUR', 'USD'):
        return f"{sym}{val:.2f}"
    return f"{val:.2f} {curr}"


def get_product_display_price(product: Product, currency: str = 'EUR') -> Tuple[float, str]:
    """Calculate the display price for a product in the target currency."""
    curr = (currency or 'EUR').upper()
    exact = product.get_price_exact(curr)
    if exact is not None:
        return float(exact), format_price(exact, curr)

    # Fallback with conversion via USD index if exact not present
    first_price = product.prices.first() if hasattr(product, 'prices') else None
    if first_price and first_price.price:
        base_val = float(first_price.price)
        base_curr = first_price.currency.upper()
        rate_in_usd = RATE_TO_USD.get(base_curr, 1.0)
        target_rate = RATE_TO_USD.get(curr, 1.0)
        converted = (base_val * rate_in_usd) / target_rate
        return round(converted, 2), format_price(Decimal(str(round(converted, 2))), curr)

    # General price property fallback
    price_val = product.get_price(curr)
    if price_val is not None:
        return float(price_val), format_price(price_val, curr)

    return 0.0, format_price(Decimal('0.00'), curr)


def serialize_chat_product(product: Product, currency: str = 'EUR') -> Dict[str, Any]:
    """Serialize product into a rich chat card payload."""
    numeric_price, formatted_price = get_product_display_price(product, currency)

    media_urls = []
    if hasattr(product, 'media'):
        for m in product.media.all()[:3]:
            url = m.get_url()
            if url:
                media_urls.append(url)

    image_url = product.get_image() or product.get_thumbnail()
    if not image_url and media_urls:
        image_url = media_urls[0]

    all_prices = []
    if hasattr(product, 'prices'):
        for p in product.prices.all():
            all_prices.append({'currency': p.currency, 'price': str(p.price)})

    return {
        'id': product.id,
        'name': product.name,
        'slug': product.slug,
        'brand_name': product.brand_name or 'Maims',
        'category_name': product.category.name if product.category else '',
        'category_slug': product.category.slug if product.category else '',
        'fabric_type': product.fabric_type or '',
        'stitching_type': product.stitching_type or '',
        'price': numeric_price,
        'formatted_price': formatted_price,
        'currency': currency.upper(),
        'image': image_url,
        'in_stock': product.is_in_stock,
        'stock': product.stock or 0,
        'size_options': product.get_size_options(),
        'color_options': product.get_color_options(),
        'length_options': product.get_length_options(),
        'description': (product.description or '')[:180],
        'average_rating': getattr(product, 'rating_average', None) or product.average_rating,
        'review_count': getattr(product, 'rating_count', None) or product.review_count,
        'prices': all_prices,
    }


class StoreKnowledge:
    """Static and dynamic store policy knowledge."""

    @staticmethod
    def get_info() -> Dict[str, Any]:
        store = SiteSettings.get()
        return {
            'store_name': store.store_name or 'Maims',
            'tagline': store.tagline or 'Curated Premium Fashion',
            'support_email': getattr(settings, 'ADMIN_RECEIVER_EMAIL', None) or 'shop@maims.eu',
            'whatsapp_number': store.whatsapp_number or '',
            'whatsapp_enabled': store.whatsapp_enabled and bool(store.whatsapp_number),
            'stripe_enabled': store.stripe_enabled,
            'paypal_enabled': store.paypal_enabled,
            'announcement': store.announcement_messages or 'Free EU shipping on orders over €40',
            'dispatch_window': '1-3 business days',
            'eu_delivery': '2-7 business days',
            'worldwide_delivery': '5-12 business days',
            'returns_window': '14 days',
            'headquarters': 'Lisbon, Portugal',
        }

    @staticmethod
    def answer_faq(topic: str) -> str:
        info = StoreKnowledge.get_info()
        t = topic.lower()

        if 'ship' in t or 'deliver' in t or 'dispatch' in t or 'courier' in t:
            return (
                f"📦 **Shipping & Delivery Information:**\n\n"
                f"• **Dispatch:** Orders are prepared and shipped from our boutique in Lisbon, Portugal within **{info['dispatch_window']}**.\n"
                f"• **European Union:** Delivery takes **{info['eu_delivery']}**.\n"
                f"• **International / Worldwide:** Delivery takes **{info['worldwide_delivery']}**.\n"
                f"• **Free Shipping:** Free shipping is offered within the EU on orders over €40!\n"
                f"You will receive live tracking information by email once your package is dispatched."
            )

        if 'return' in t or 'refund' in t or 'exchange' in t or 'cancel' in t:
            return (
                f"🔄 **Returns & Refund Policy:**\n\n"
                f"• We provide a **{info['returns_window']} return window** from the day your package arrives.\n"
                f"• Garments must be unworn, unwashed, and in original condition with all brand tags and packaging intact.\n"
                f"• To begin a return or exchange, simply email our customer team at **{info['support_email']}** or message us on WhatsApp with your Order ID.\n"
                f"• Refunds are processed back to your original payment method within 3–5 business days of inspection."
            )

        if 'pay' in t or 'stripe' in t or 'card' in t or 'paypal' in t or 'cod' in t:
            methods = []
            if info['stripe_enabled']:
                methods.append("• **Credit / Debit Cards (Stripe):** Visa, Mastercard, American Express with 3D Secure encryption.")
            if info['paypal_enabled']:
                methods.append("• **PayPal:** Fast, secure one-click checkout.")
            if info['whatsapp_enabled']:
                methods.append("• **WhatsApp Concierge Ordering:** Place your order directly in chat with our team.")
            methods_str = "\n".join(methods) if methods else "• Card payments and WhatsApp ordering are supported."
            return (
                f"💳 **Accepted Payment Methods:**\n\n"
                f"{methods_str}\n\n"
                f"All payments are SSL-encrypted and processed through verified PCI-DSS compliant providers."
            )

        if 'size' in t or 'measurement' in t or 'fit' in t:
            return (
                f"📏 **Sizing & Measurement Guide:**\n\n"
                f"• **Ready-to-Wear (Pret):** S (Bust 36\"), M (Bust 38\"), L (Bust 40-42\"), XL (Bust 44\"), and XXL (Bust 46-50\").\n"
                f"• **Unstitched Suits:** Generous fabric cuts including shirt fabric (approx 3m), dupatta (2.5m), and trouser fabric (2.5m) suitable for custom tailoring up to size 52+.\n"
                f"• Check the size selector on each product page for item-specific length and bust options.\n"
                f"• Need a custom fit or sizing confirmation? Our stylists are happy to advise you on WhatsApp!"
            )

        if 'care' in t or 'wash' in t or 'fabric' in t or 'iron' in t:
            return (
                f"✨ **Fabric Care Guide:**\n\n"
                f"• **Jamdani & Pure Silk:** Dry clean only to preserve delicate weave and metallic zari embroidery.\n"
                f"• **Organza & Chiffon:** Gentle dry clean or hand wash in cold water with mild detergent. Do not wring.\n"
                f"• **Velvet:** Professional dry clean only; steam inside out to restore pile.\n"
                f"• **Cotton & Premium Lawn:** Machine wash gentle on cold or hand wash, dry in shade to maintain color brilliance."
            )

        return (
            f"ℹ️ **About {info['store_name']}:**\n\n"
            f"{info['tagline']}. Based in {info['headquarters']}, we bring you the finest Pakistani and South Asian designerwear, "
            f"heritage handlooms, and contemporary festive collections.\n"
            f"For support, reach out to **{info['support_email']}**."
        )


class ChatbotAgent:
    """Autonomous E-Commerce Assistant with Dual-Engine (LLM + Built-in NLU)."""

    def __init__(self, currency: str = 'EUR', user=None, session_id: Optional[str] = None):
        self.currency = (currency or 'EUR').upper()
        self.user = user
        self.session_id = session_id or 'anon'
        self.context_key = f"maims_chatbot_session_{self.session_id}"

    # --- Session Context Management ---
    def get_context(self) -> Dict[str, Any]:
        return cache.get(self.context_key) or {
            'history': [],
            'last_intent': None,
            'last_filters': {},
            'last_order_id': None,
        }

    def update_context(self, updates: Dict[str, Any]):
        ctx = self.get_context()
        ctx.update(updates)
        cache.set(self.context_key, ctx, timeout=3600)  # 1 hour persistence

    # --- Database Tools ---
    def search_products(
        self,
        query: str = '',
        category: str = '',
        fabric: str = '',
        stitching: str = '',
        size: str = '',
        color: str = '',
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        limit: int = 6,
    ) -> List[Dict[str, Any]]:
        """Search products in DB with faceted filters."""
        qs = Product.objects.filter(is_visible=True).annotate(
            rating_average=Avg('reviews__rating', filter=Q(reviews__is_approved=True)),
            rating_count=Count('reviews', distinct=True, filter=Q(reviews__is_approved=True)),
        ).prefetch_related(
            'prices',
            'media',
            Prefetch(
                'category',
                queryset=Category.objects.annotate(product_count=Count('products')).prefetch_related('children'),
            ),
        )

        if query:
            q_clean = query.strip()
            # Stop words filter for search query
            stop_words = {'show', 'me', 'the', 'a', 'an', 'i', 'want', 'looking', 'for', 'find', 'any', 'some', 'please', 'product', 'products', 'item', 'items'}
            tokens = [w for w in re.findall(r'\b[a-zA-Z0-9]+\b', q_clean.lower()) if w not in stop_words]

            if tokens:
                filter_q = Q()
                for token in tokens:
                    filter_q |= (
                        Q(name__icontains=token)
                        | Q(brand_name__icontains=token)
                        | Q(description__icontains=token)
                        | Q(category__name__icontains=token)
                        | Q(fabric_type__icontains=token)
                        | Q(material_type__icontains=token)
                    )
                qs = qs.filter(filter_q)

        if category:
            qs = qs.filter(Q(category__name__icontains=category) | Q(category__slug__icontains=category))

        if fabric:
            qs = qs.filter(Q(fabric_type__iexact=fabric) | Q(description__icontains=fabric))

        if stitching:
            if stitching in ('unstitched', 'ready_to_wear'):
                qs = qs.filter(Q(stitching_type=stitching) | Q(stitching_type='both'))
            else:
                qs = qs.filter(stitching_type__icontains=stitching)

        if size:
            qs = qs.filter(size_options__icontains=size)

        if color:
            qs = qs.filter(Q(color_options__icontains=color) | Q(name__icontains=color) | Q(description__icontains=color))

        products = list(qs.distinct()[:25])

        # Filter by price in memory using accurate converted prices
        filtered = []
        for p in products:
            numeric_price, _ = get_product_display_price(p, self.currency)
            if min_price is not None and numeric_price < min_price:
                continue
            if max_price is not None and numeric_price > max_price:
                continue
            filtered.append(p)

        # Fallback if over-filtered: return top candidates without strict price filtering
        if not filtered and products and (min_price is not None or max_price is not None):
            filtered = products

        return [serialize_chat_product(p, self.currency) for p in filtered[:limit]]

    def get_product_details(self, identifier: str) -> Optional[Dict[str, Any]]:
        """Look up single product by slug or id."""
        qs = Product.objects.filter(is_visible=True).prefetch_related('prices', 'media', 'category')
        product = None
        if identifier.isdigit():
            product = qs.filter(id=int(identifier)).first()
        if not product:
            product = qs.filter(slug=identifier).first()
        if not product:
            product = qs.filter(name__icontains=identifier).first()

        if product:
            return serialize_chat_product(product, self.currency)
        return None

    def track_order(
        self,
        order_id: int,
        email: Optional[str] = None,
        phone: Optional[str] = None
    ) -> Dict[str, Any]:
        """Look up order safely with privacy checks."""
        order = (
            Order.objects.filter(id=order_id)
            .prefetch_related(
                Prefetch(
                    'items__product',
                    queryset=Product.objects.prefetch_related('prices', 'media'),
                )
            )
            .first()
        )
        if not order:
            return {'found': False, 'message': f"We couldn't find an order matching #{order_id}. Please check the number and try again."}

        # Privacy check: caller is authenticated owner OR provided matching email/phone
        is_owner = False
        if self.user and self.user.is_authenticated and order.user == self.user:
            is_owner = True
        elif email and email.strip().lower() == order.email.strip().lower():
            is_owner = True
        elif phone and phone.strip() in order.phone.strip():
            is_owner = True

        status_messages = {
            'new': "Received and waiting for confirmation by our team.",
            'accepted': "Confirmed! Your order has been approved and sent to our atelier for packing.",
            'packed': "Carefully packed in signature Maims luxury packaging and awaiting courier pickup.",
            'shipped': "On its way! Your package has been dispatched from Lisbon, Portugal.",
            'delivered': "Delivered! We hope you love your new outfit.",
            'cancelled': "This order was cancelled.",
            'rejected': "This order could not be fulfilled.",
            'returned': "Returned and processed for refund.",
        }

        friendly_status = status_messages.get(order.status, order.get_status_display())

        items_summary = []
        for it in order.items.all():
            items_summary.append({
                'name': it.product.name,
                'quantity': it.quantity,
                'size': it.size or 'Standard',
                'price': format_price(it.price, order.currency),
            })

        if not is_owner:
            # Masked privacy mode: safe summary
            first_initial = order.first_name[0] if order.first_name else 'Customer'
            return {
                'found': True,
                'verified': False,
                'order_id': order.id,
                'status': order.status,
                'status_label': friendly_status,
                'date': order.created_at.strftime('%B %d, %Y'),
                'total': format_price(order.total_amount, order.currency),
                'item_count': order.items.count(),
                'masked_recipient': f"{first_initial}*** from {order.place or 'EU'}",
                'message': (
                    f"Order **#{order.id}** is currently: **{order.status.upper()}**.\n\n"
                    f"**Status:** {friendly_status}\n"
                    f"**Date:** {order.created_at.strftime('%b %d, %Y')}\n"
                    f"**Total:** {format_price(order.total_amount, order.currency)}\n\n"
                    f"*(For security, please provide the email or phone number used at checkout to see full shipping address and item details.)*"
                ),
            }

        return {
            'found': True,
            'verified': True,
            'order_id': order.id,
            'status': order.status,
            'status_label': friendly_status,
            'date': order.created_at.strftime('%B %d, %Y'),
            'total': format_price(order.total_amount, order.currency),
            'currency': order.currency,
            'payment_method': order.payment_method_label,
            'is_paid': order.is_paid,
            'shipping_address': f"{order.address}, {order.zipcode} {order.place}",
            'items': items_summary,
            'message': (
                f"✅ **Order #{order.id} Details**\n\n"
                f"• **Status:** {friendly_status}\n"
                f"• **Placed on:** {order.created_at.strftime('%B %d, %Y')}\n"
                f"• **Payment:** {order.payment_method_label} ({'Paid' if order.is_paid else 'Pending Payment'})\n"
                f"• **Delivery to:** {order.first_name} {order.last_name}, {order.address}, {order.place}\n\n"
                f"**Items ({len(items_summary)}):**\n"
                + "\n".join([f"- {it['quantity']}x {it['name']} ({it['size']}) — {it['price']}" for it in items_summary])
            ),
        }

    def get_whatsapp_action(self, prefill: str = '') -> Dict[str, Any]:
        """Build WhatsApp concierge URL and action payload."""
        store = SiteSettings.get()
        if not (store.whatsapp_enabled and store.whatsapp_number):
            return {
                'enabled': False,
                'message': "WhatsApp ordering is not configured at the moment. Please contact shop@maims.eu for assistance.",
            }
        msg = prefill or store.whatsapp_greeting or "Hello Maims! I would like personal styling assistance."
        link = store.whatsapp_link(msg)
        return {
            'enabled': True,
            'url': link,
            'number': store.whatsapp_number,
            'label': "Chat on WhatsApp",
        }

    # --- Built-in Rule / NLU Engine ---
    def process_nlu(self, message: str) -> Dict[str, Any]:
        """Intelligent zero-dependency natural language e-commerce processor."""
        msg = message.strip()
        msg_lower = msg.lower()
        ctx = self.get_context()

        # 1. Greetings
        if re.search(r'\b(hi|hello|hey|salaam|assalam|namaste|hola|bonjour|greetings)\b', msg_lower) and len(msg_lower.split()) <= 4:
            welcome_products = self.search_products(limit=4)
            return {
                'reply': (
                    "Hello and welcome to **Maims**! ✨\n\n"
                    "I am your personal AI shopping stylist and concierge. I can help you:\n"
                    "• **Find styles:** Discover pure silk sarees, luxury lawn suits, organza festive wear, or bridal collections.\n"
                    "• **Track orders:** Check real-time shipping status for any order.\n"
                    "• **Style & Sizing advice:** Guide you on bust measurements, ready-to-wear vs unstitched pieces.\n"
                    "• **Store policies:** Clarify shipping times, returns, and payment options.\n\n"
                    "What can I help you discover today?"
                ),
                'products': welcome_products,
                'suggestions': [
                    "Show latest arrivals",
                    "Do you have pure silk sarees?",
                    "Track my order",
                    "What is your delivery time?",
                ],
                'action': None,
            }

        # 2. Order Tracking
        order_match = re.search(r'(?:order\s*(?:#|number|id)?|#)\s*([0-9]{1,8})\b', msg_lower)
        email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', msg)
        phone_match = re.search(r'(?:\+?\d{8,15})', msg)

        if order_match or 'track' in msg_lower or 'where is my order' in msg_lower or 'order status' in msg_lower:
            order_id = int(order_match.group(1)) if order_match else ctx.get('last_order_id')
            if not order_id and self.user and self.user.is_authenticated:
                recent = Order.objects.filter(user=self.user).order_by('-created_at').first()
                if recent:
                    order_id = recent.id

            if order_id:
                self.update_context({'last_order_id': order_id})
                tracking = self.track_order(
                    order_id,
                    email=email_match.group(0) if email_match else None,
                    phone=phone_match.group(0) if phone_match else None,
                )
                suggestions = ["Track another order", "Shipping time info", "Return policy", "Show latest arrivals"]
                return {
                    'reply': tracking['message'],
                    'products': [],
                    'suggestions': suggestions,
                    'action': {'type': 'order_tracked', 'order_id': order_id, 'status': tracking.get('status')} if tracking.get('found') else None,
                }
            else:
                return {
                    'reply': (
                        "I would be glad to check your order status! 📦\n\n"
                        "Please provide your **Order Number** (e.g. *#1024*) and the **email address** used at checkout."
                    ),
                    'products': [],
                    'suggestions': ["Show latest arrivals", "How long does shipping take?", "Contact WhatsApp support"],
                    'action': None,
                }

        # 3. Store Policies & FAQ
        for topic in ('ship', 'deliver', 'dispatch', 'return', 'refund', 'exchange', 'pay', 'stripe', 'paypal', 'size', 'sizing', 'care', 'wash'):
            if topic in msg_lower:
                faq_answer = StoreKnowledge.answer_faq(topic)
                return {
                    'reply': faq_answer,
                    'products': [],
                    'suggestions': [
                        "Show latest arrivals",
                        "Chat with support on WhatsApp",
                        "Track an order",
                        "How do I choose my size?",
                    ],
                    'action': None,
                }

        # 4. WhatsApp / Human Concierge Request
        if re.search(r'\b(whatsapp|human|agent|representative|call|phone|talk to someone|custom order|bridal)\b', msg_lower):
            wa = self.get_whatsapp_action(f"Hello Maims! I am chatting with your AI assistant and would like personal assistance: '{msg[:60]}'")
            reply = (
                "Our dedicated stylists and customer concierge team are available directly on WhatsApp for:\n"
                "• Custom bridal and festive tailoring\n"
                "• Sizing and styling consultations\n"
                "• Direct order placement and local pickup arrangements\n\n"
                "Click the button below to start a direct WhatsApp conversation with us! 💬"
            ) if wa['enabled'] else wa['message']
            return {
                'reply': reply,
                'products': [],
                'suggestions': ["Show silk collections", "Show festive suits", "Track an order"],
                'action': {'type': 'whatsapp', 'url': wa.get('url')} if wa['enabled'] else None,
            }

        # 5. Product Discovery & Recommendations
        # Extract fabric entities
        fabrics = ['lawn', 'silk', 'organza', 'velvet', 'cotton', 'chiffon', 'linen']
        found_fabric = next((f for f in fabrics if f in msg_lower), '')

        # Extract stitching
        stitching = ''
        if 'unstitched' in msg_lower:
            stitching = 'unstitched'
        elif 'ready to wear' in msg_lower or 'stitched' in msg_lower or 'pret' in msg_lower:
            stitching = 'ready_to_wear'

        # Extract price constraints
        max_price = None
        min_price = None
        price_under = re.search(r'(?:under|below|less than|max|up to)\s*([0-9]+(?:\.[0-9]{1,2})?)', msg_lower)
        price_between = re.search(r'between\s*([0-9]+)\s*and\s*([0-9]+)', msg_lower)
        if price_under:
            max_price = float(price_under.group(1))
        elif price_between:
            min_price = float(price_between.group(1))
            max_price = float(price_between.group(2))
        elif 'cheap' in msg_lower or 'budget' in msg_lower or 'affordable' in msg_lower:
            max_price = 70.0 if self.currency in ('EUR', 'USD') else None

        # Extract color
        colors = ['red', 'blue', 'green', 'black', 'white', 'pink', 'yellow', 'gold', 'emerald', 'maroon', 'purple', 'navy', 'beige']
        found_color = next((c for c in colors if c in msg_lower), '')

        # Extract sizes
        sizes = ['s', 'm', 'l', 'xl', 'xxl', '36', '38', '40', '42', '44', '46', '48', '50']
        found_size = next((s for s in sizes if re.search(rf'\b(?:size\s*)?{s}\b', msg_lower)), '')

        # Extract category
        categories = ['saree', 'sari', 'kurti', 'suit', 'dress', 'jewelry', 'jewellery', 'bag', 'dupatta', 'shawl', 'lehenga']
        found_category = next((c for c in categories if c in msg_lower), '')

        # Build clean search term
        cleaned_query = msg
        for kw in fabrics + colors + categories + ['under', 'below', 'cheap', 'unstitched', 'ready to wear', 'size', 'looking', 'for', 'show', 'me']:
            cleaned_query = re.sub(rf'\b{kw}\b', '', cleaned_query, flags=re.IGNORECASE)
        cleaned_query = cleaned_query.strip()

        products = self.search_products(
            query=cleaned_query,
            category=found_category,
            fabric=found_fabric,
            stitching=stitching,
            size=found_size,
            color=found_color,
            min_price=min_price,
            max_price=max_price,
            limit=6,
        )

        if products:
            desc_parts = []
            if found_fabric:
                desc_parts.append(f"{found_fabric.title()} fabric")
            if found_color:
                desc_parts.append(f"{found_color.title()} tones")
            if stitching:
                desc_parts.append("Ready-to-wear" if stitching == 'ready_to_wear' else "Unstitched")
            if max_price:
                desc_parts.append(f"under {format_price(Decimal(str(max_price)), self.currency)}")

            spec = f" featuring {', '.join(desc_parts)}" if desc_parts else ""
            reply = (
                f"I found {len(products)} stunning selection{'s' if len(products) > 1 else ''}{spec} "
                f"from our catalogue:\n\n"
                f"Feel free to click any product to view full details or add it directly to your shopping bag."
            )
            return {
                'reply': reply,
                'products': products,
                'suggestions': [
                    "Do you have this in other colors?",
                    "What sizes are available?",
                    "Show unstitched suits",
                    "How long does shipping take?",
                ],
                'action': None,
            }

        # Fallback if no matching product was found
        popular = self.search_products(limit=4)
        return {
            'reply': (
                f"I couldn't find an exact match for **\"{msg}\"**, but here are some of our most loved "
                f"and popular pieces you might adore! ✨\n\n"
                f"You can also ask about fabrics (*Lawn, Silk, Organza, Velvet*), or chat with our styling team on WhatsApp for custom requests."
            ),
            'products': popular,
            'suggestions': [
                "Show silk sarees",
                "Show unstitched lawn",
                "Contact WhatsApp stylist",
                "Track an order",
            ],
            'action': None,
        }

    # --- LLM Provider Integration (OpenAI-compatible) ---
    def call_llm(self, message: str) -> Optional[Dict[str, Any]]:
        """Call external LLM if configured; returns None on failure/missing key."""
        api_key = (
            getattr(settings, 'OPENAI_API_KEY', None)
            or os.environ.get('OPENAI_API_KEY')
            or os.environ.get('LLM_API_KEY')
            or os.environ.get('GROQ_API_KEY')
        )
        if not api_key:
            return None

        base_url = os.environ.get('LLM_BASE_URL', 'https://api.openai.com/v1').rstrip('/')
        model_name = os.environ.get('LLM_MODEL', 'gpt-4o-mini')

        tools = [
            {
                "type": "function",
                "function": {
                    "name": "search_products",
                    "description": "Search products in Maims e-commerce catalogue by text, category, fabric, stitching, size, color, and price bounds.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "Free-text keywords (e.g. 'Jamdani', 'Maria.B', 'Festive Kurti')"},
                            "category": {"type": "string", "description": "Category name or slug (e.g. 'women', 'sarees', 'jewellery')"},
                            "fabric": {"type": "string", "description": "Fabric type: lawn, silk, organza, velvet, cotton, chiffon, other"},
                            "stitching": {"type": "string", "description": "unstitched or ready_to_wear"},
                            "size": {"type": "string", "description": "Size option (S, M, L, XL, 36, 38, etc.)"},
                            "color": {"type": "string", "description": "Color name or tone (red, green, gold, emerald...)"},
                            "max_price": {"type": "number", "description": "Maximum price in user's currency"},
                            "min_price": {"type": "number", "description": "Minimum price in user's currency"}
                        }
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "track_order",
                    "description": "Look up an existing customer order by order ID and optional email or phone.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "order_id": {"type": "integer", "description": "Order ID number"},
                            "email": {"type": "string", "description": "Customer email address for verification"},
                            "phone": {"type": "string", "description": "Customer phone number for verification"}
                        },
                        "required": ["order_id"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_store_policy",
                    "description": "Retrieve verified store policy details regarding shipping, delivery, returns, payments, size guide, or fabric care.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "topic": {"type": "string", "description": "shipping, returns, payment, sizing, or fabric_care"}
                        },
                        "required": ["topic"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_whatsapp_concierge",
                    "description": "Get direct WhatsApp link for personal styling, bridal inquiries, or manual checkout.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "reason": {"type": "string", "description": "Reason for WhatsApp contact"}
                        }
                    }
                }
            }
        ]

        system_prompt = (
            f"You are the official AI Fashion Stylist & Concierge for 'Maims', a luxury South Asian & contemporary designer fashion boutique based in Lisbon, Portugal.\n"
            f"Active customer currency: {self.currency}.\n"
            f"Guidelines:\n"
            f"1. Be elegant, warm, sophisticated, and helpful. Guide customers on fabrics (Jamdani, Silk, Lawn, Organza, Velvet, Chiffon), styling, sizing, and occasions.\n"
            f"2. ALWAYS call `search_products` when a user expresses any interest in clothing, outfits, prices, styles, or collections.\n"
            f"3. When customers ask about their order, use `track_order`.\n"
            f"4. For policy questions (shipping, returns, sizing charts), use `get_store_policy`.\n"
            f"5. Mention that all garments ship safely from Lisbon, Portugal with fast EU delivery.\n"
            f"6. Never invent non-existent products or order statuses."
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": message}
        ]

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        try:
            resp = requests.post(
                f"{base_url}/chat/completions",
                headers=headers,
                json={
                    "model": model_name,
                    "messages": messages,
                    "tools": tools,
                    "tool_choice": "auto",
                    "temperature": 0.4,
                    "max_tokens": 800,
                },
                timeout=12,
            )
            if resp.status_code != 200:
                logger.warning("LLM API returned status %s: %s", resp.status_code, resp.text[:200])
                return None

            data = resp.json()
            choice = data.get('choices', [{}])[0]
            msg_obj = choice.get('message', {})
            tool_calls = msg_obj.get('tool_calls', [])

            collected_products: List[Dict[str, Any]] = []
            action_payload = None

            if tool_calls:
                messages.append(msg_obj)
                for tc in tool_calls:
                    fn_name = tc.get('function', {}).get('name')
                    try:
                        args = json.loads(tc.get('function', {}).get('arguments', '{}'))
                    except Exception:
                        args = {}

                    tool_result_content = ""
                    if fn_name == 'search_products':
                        prods = self.search_products(
                            query=args.get('query', ''),
                            category=args.get('category', ''),
                            fabric=args.get('fabric', ''),
                            stitching=args.get('stitching', ''),
                            size=args.get('size', ''),
                            color=args.get('color', ''),
                            min_price=args.get('min_price'),
                            max_price=args.get('max_price'),
                        )
                        collected_products.extend(prods)
                        tool_result_content = json.dumps([
                            {'id': p['id'], 'name': p['name'], 'price': p['formatted_price'], 'in_stock': p['in_stock']}
                            for p in prods
                        ])

                    elif fn_name == 'track_order':
                        res = self.track_order(
                            order_id=args.get('order_id', 0),
                            email=args.get('email'),
                            phone=args.get('phone'),
                        )
                        tool_result_content = json.dumps(res)
                        if res.get('found'):
                            action_payload = {'type': 'order_tracked', 'order_id': args.get('order_id')}

                    elif fn_name == 'get_store_policy':
                        res = StoreKnowledge.answer_faq(args.get('topic', ''))
                        tool_result_content = res

                    elif fn_name == 'get_whatsapp_concierge':
                        wa = self.get_whatsapp_action(args.get('reason', ''))
                        tool_result_content = json.dumps(wa)
                        if wa.get('enabled'):
                            action_payload = {'type': 'whatsapp', 'url': wa.get('url')}

                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc.get('id'),
                        "content": tool_result_content or "Success",
                    })

                # Follow-up completion after tool results
                second_resp = requests.post(
                    f"{base_url}/chat/completions",
                    headers=headers,
                    json={
                        "model": model_name,
                        "messages": messages,
                        "temperature": 0.4,
                        "max_tokens": 600,
                    },
                    timeout=12,
                )
                if second_resp.status_code == 200:
                    final_choice = second_resp.json().get('choices', [{}])[0]
                    final_text = final_choice.get('message', {}).get('content', '')
                    return {
                        'reply': final_text,
                        'products': collected_products[:6],
                        'suggestions': [
                            "Show pure silk sarees",
                            "Track another order",
                            "What is your return policy?",
                            "Chat on WhatsApp",
                        ],
                        'action': action_payload,
                    }

            final_text = msg_obj.get('content', '')
            if final_text:
                return {
                    'reply': final_text,
                    'products': collected_products[:6],
                    'suggestions': ["Show latest arrivals", "Track my order", "Delivery information"],
                    'action': action_payload,
                }

        except Exception as exc:
            logger.warning("LLM call failed with error: %s. Falling back to built-in agent.", str(exc))

        return None

    # --- Main Agent Dispatch ---
    def respond(self, message: str) -> Dict[str, Any]:
        """Process incoming user query and return comprehensive agent response."""
        # Try external LLM first if configured
        llm_result = self.call_llm(message)
        if llm_result:
            return llm_result

        # Built-in intelligent NLU agent (always succeeds and returns within milliseconds)
        return self.process_nlu(message)
