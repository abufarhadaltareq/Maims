<template>
  <div class="py-10 px-4 sm:px-6 max-w-6xl mx-auto font-brand text-brand-text">

    <!-- Header -->
    <div class="flex flex-wrap items-end justify-between gap-4 mb-8">
      <div>
        <h1 class="text-3xl sm:text-4xl font-extrabold tracking-tight">Your Shopping Bag</h1>
        <p class="text-gray-500 mt-1">
          {{ cartStore.cartTotalLength }} {{ cartStore.cartTotalLength === 1 ? 'item' : 'items' }}
        </p>
      </div>
      <router-link
        to="/"
        class="inline-flex items-center gap-1.5 text-sm font-semibold text-brand-accent hover:underline"
      >
        <svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M15 19l-7-7 7-7"/></svg>
        Continue shopping
      </router-link>
    </div>

    <!-- Empty state -->
    <div v-if="cartStore.items.length === 0" class="text-center py-20 border border-dashed border-gray-200 rounded-3xl bg-gray-50/50">
      <div class="w-16 h-16 mx-auto mb-5 rounded-full bg-brand-muted flex items-center justify-center">
        <svg class="w-8 h-8 text-gray-400" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" d="M15.75 10.5V6a3.75 3.75 0 10-7.5 0v4.5m11.356-1.993l1.263 12c.07.665-.45 1.243-1.119 1.243H4.25a1.125 1.125 0 01-1.12-1.243l1.264-12A1.125 1.125 0 015.513 7.5h12.974c.576 0 1.059.435 1.119 1.007z"/>
        </svg>
      </div>
      <p class="text-gray-600 font-semibold text-lg mb-1">Your bag is currently empty.</p>
      <p class="text-gray-400 text-sm mb-6">Fresh drops are waiting in the collections.</p>
      <ExploreButton>Explore Collections</ExploreButton>
    </div>

    <div v-else class="grid grid-cols-1 lg:grid-cols-3 gap-8 items-start">

      <!-- ===== Bag items ===== -->
      <div class="lg:col-span-2 space-y-5">
        <div
          v-for="item in cartStore.items"
          :key="`${item.product?.id || item.id}-${item.variant || item.size || 'default'}`"
          class="group flex gap-4 sm:gap-5 p-4 sm:p-5 bg-white border border-gray-100 rounded-2xl shadow-sm hover:shadow-brand transition-all duration-300"
        >
          <!-- Clickable product image -->
          <router-link
            :to="productLink(item)"
            class="block w-24 h-28 sm:w-28 sm:h-32 rounded-xl overflow-hidden bg-brand-muted flex-shrink-0"
            :title="`View ${item.product?.name || 'product'}`"
          >
            <img
              :src="item.product?.get_thumbnail || 'https://placehold.co/160x200'"
              :alt="item.product?.name || 'Product Image'"
              class="w-full h-full object-cover object-center group-hover:scale-105 transition duration-500"
              loading="lazy"
            />
          </router-link>

          <div class="flex-1 min-w-0">
            <div class="flex items-start justify-between gap-3">
              <div class="min-w-0">
                <!-- Clickable product name -->
                <router-link
                  :to="productLink(item)"
                  class="font-bold text-base leading-tight hover:text-brand-accent hover:underline"
                >
                  {{ item.product?.name }}
                </router-link>
                <p class="text-sm text-gray-500 font-medium">{{ getItemDisplayPrice(item).string }} each</p>
                <p v-if="item.variant || item.size" class="text-xs font-bold text-slate-700 mt-1">{{ item.variant || item.size }}</p>

                <!-- Star rating (admin moderates reviews) -->
                <p v-if="item.product?.average_rating != null" class="text-xs text-amber-500 font-bold mt-0.5">
                  ★ {{ item.product.average_rating.toFixed(1) }}
                  <span class="text-gray-400 font-semibold">({{ item.product?.review_count || 0 }} reviews)</span>
                </p>

                <!-- Admin-managed attributes -->
                <div class="flex flex-wrap gap-1.5 mt-2">
                  <span v-if="item.product?.brand_name" class="text-[10px] font-bold uppercase tracking-wider text-gray-500 bg-gray-100 rounded-full px-2 py-0.5">
                    {{ item.product.brand_name }}
                  </span>
                  <span v-if="stitchingLabel(item)" class="text-[10px] font-bold uppercase tracking-wider text-gray-500 bg-gray-100 rounded-full px-2 py-0.5">
                    {{ stitchingLabel(item) }}
                  </span>
                  <span v-if="item.product?.fabric_type" class="text-[10px] font-bold uppercase tracking-wider text-gray-500 bg-gray-100 rounded-full px-2 py-0.5">
                    {{ item.product.fabric_type }}
                  </span>
                </div>
              </div>

              <!-- Line total + remove -->
              <div class="text-right flex-shrink-0">
                <p class="font-extrabold text-base whitespace-nowrap">{{ lineTotal(item) }}</p>
                <button
                  @click="cartStore.removeItem(item.product?.id, item.size)"
                  class="mt-1 inline-flex items-center gap-1 text-xs text-gray-400 hover:text-red-600 transition"
                >
                  <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M14.74 9l-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 01-2.244 2.077H8.084a2.25 2.25 0 01-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 00-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 013.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 00-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916"/></svg>
                  Remove
                </button>
              </div>
            </div>

            <!-- Stock status (admin-managed inventory) -->
            <p v-if="isOutOfStock(item)" class="mt-2 inline-flex items-center gap-1.5 text-xs font-bold text-red-600 bg-red-50 rounded-full px-2.5 py-1">
              <span class="w-1.5 h-1.5 rounded-full bg-red-500"></span>Out of stock
            </p>
            <p v-else-if="isLowStock(item)" class="mt-2 inline-flex items-center gap-1.5 text-xs font-bold text-amber-600 bg-amber-50 rounded-full px-2.5 py-1">
              <span class="w-1.5 h-1.5 rounded-full bg-amber-500"></span>Only {{ item.product.stock }} left
            </p>
            <p v-else-if="item.product?.stock != null" class="mt-2 inline-flex items-center gap-1.5 text-xs font-bold text-emerald-600 bg-emerald-50 rounded-full px-2.5 py-1">
              <span class="w-1.5 h-1.5 rounded-full bg-emerald-500"></span>In stock
            </p>

            <!-- Controls: size (admin-managed options) + quantity -->
            <div class="flex flex-wrap items-center gap-3 mt-3">
              <select
                v-if="sizeOptions(item).length"
                :value="item.size || ''"
                @change="changeSize(item, $event)"
                class="text-sm font-semibold border border-gray-200 rounded-lg px-2.5 py-1.5 bg-white focus:outline-brand"
                aria-label="Size"
              >
                <option value="" disabled>Select size</option>
                <option v-for="size in sizeOptions(item)" :key="size" :value="size">{{ size }}</option>
              </select>

              <div class="flex items-center gap-1.5">
                <button
                  @click="cartStore.decrementQuantity(item.product?.id, item.size)"
                  class="w-8 h-8 flex items-center justify-center border border-gray-200 rounded-lg text-gray-600 hover:bg-gray-50 active:bg-gray-100 transition font-bold"
                  aria-label="Decrease quantity"
                >−</button>
                <input
                  :value="item.quantity"
                  @change="(e) => cartStore.setQuantity(item.product?.id, item.size, e.target.value)"
                  type="number" min="1" max="99"
                  class="w-12 text-center font-bold text-sm border border-gray-200 rounded-lg py-1.5 focus:outline-brand"
                  aria-label="Quantity"
                />
                <button
                  @click="cartStore.incrementQuantity(item.product?.id, item.size)"
                  :disabled="atStockCap(item)"
                  title="Add one"
                  class="w-8 h-8 flex items-center justify-center border border-gray-200 rounded-lg text-gray-600 hover:bg-gray-50 active:bg-gray-100 transition font-bold disabled:opacity-40"
                  aria-label="Increase quantity"
                >+</button>
              </div>
            </div>
          </div>
        </div>

        <div class="flex flex-wrap items-center justify-between gap-3 pt-1">
          <button
            @click="cartStore.clearCart"
            class="text-xs text-red-500 font-semibold underline hover:text-red-700 transition"
          >
            Clear entire shopping bag
          </button>
          <span class="text-xs text-gray-400">Prices in {{ cartStore.currentCurrency }} — change at the top of the page.</span>
        </div>
      </div>

      <!-- ===== Order summary ===== -->
      <aside class="bg-gray-50/70 border border-gray-100 rounded-2xl p-6 space-y-4 lg:sticky lg:top-24">
        <h2 class="font-bold text-lg tracking-tight">Order Summary</h2>

        <!-- Payment methods the shop has enabled (admin toggles) -->
        <div class="flex flex-wrap gap-2">
          <span v-if="site.stripeEnabled" class="inline-flex items-center gap-1.5 text-[11px] font-bold text-gray-600 bg-white border border-gray-200 rounded-full px-2.5 py-1">
            <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M2.25 8.25h19.5M2.25 9h19.5m-16.5 5.25h6m-6 2.25h3m-3.75 3h15a2.25 2.25 0 002.25-2.25V6.75A2.25 2.25 0 0019.5 4.5h-15a2.25 2.25 0 00-2.25 2.25v10.5A2.25 2.25 0 004.5 19.5z"/></svg>
            Card
          </span>
          <span v-if="site.paypalEnabled" class="inline-flex items-center gap-1.5 text-[11px] font-bold text-gray-600 bg-white border border-gray-200 rounded-full px-2.5 py-1">
            <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M17 9V7a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2m2 4h10a2 2 0 002-2v-6a2 2 0 00-2-2H9a2 2 0 00-2 2v6a2 2 0 002 2zm7-5a2 2 0 11-4 0 2 2 0 014 0z"/></svg>
            PayPal
          </span>
          <span v-if="site.whatsappEnabled" class="inline-flex items-center gap-1.5 text-[11px] font-bold text-gray-600 bg-white border border-gray-200 rounded-full px-2.5 py-1">
            <svg class="w-3.5 h-3.5" fill="currentColor" viewBox="0 0 24 24"><path d="M12 2a10 10 0 00-8.6 15.1L2 22l5-1.3A10 10 0 1012 2zm5.4 14.1c-.2.6-1.3 1.2-1.8 1.2-.5.1-1 .2-3.4-.7-2.9-1.2-4.7-4.1-4.9-4.3-.1-.2-1.2-1.6-1.2-3.1s.8-2.2 1-2.5c.3-.3.6-.4.8-.4h.6c.2 0 .4 0 .6.5s.8 1.9.8 2c.1.1.1.3 0 .5-.3.6-.6.8-.4 1.1.6 1.1 1.4 1.8 2.4 2.4.3.2.5.1.7-.1l.8-.9c.2-.3.4-.2.7-.1l2 1c.3.1.5.2.6.4 0 .1 0 .6-.5 1.5z"/></svg>
            WhatsApp
          </span>
        </div>

        <div class="flex justify-between text-sm text-gray-600 font-medium">
          <span>Total Items:</span>
          <span>{{ cartStore.cartTotalLength }} items</span>
        </div>

        <div class="flex justify-between text-sm text-gray-600 font-medium">
          <span>Shipping:</span>
          <span class="text-emerald-600 font-semibold">Free</span>
        </div>

        <hr class="border-gray-200" />

        <div class="flex justify-between items-baseline">
          <span class="font-bold text-base">Estimated Total:</span>
          <span class="font-black text-2xl text-brand">{{ cartTotalDisplayPrice }}</span>
        </div>

        <p v-if="hasOutOfStock" class="text-xs font-semibold text-red-600 bg-red-50 rounded-lg px-3 py-2">
          Some items in your bag are out of stock — remove them to place the order.
        </p>

        <router-link
          to="/checkout"
          :class="hasOutOfStock ? 'opacity-40 pointer-events-none' : ''"
          class="block w-full text-center bg-gradient-brand text-white font-bold py-3.5 rounded-xl shadow hover:brightness-110 transition duration-200 mt-1"
        >
          Proceed to Checkout
        </router-link>

        <a
          v-if="site.whatsappEnabled && whatsappCartLink"
          :href="whatsappCartLink"
          target="_blank" rel="noopener"
          class="flex items-center justify-center gap-2 w-full text-center bg-gradient-brand text-white font-bold py-3 rounded-xl shadow hover:brightness-95 transition duration-200"
        >
          <svg class="w-5 h-5" fill="currentColor" viewBox="0 0 24 24"><path d="M12 2a10 10 0 00-8.6 15.1L2 22l5-1.3A10 10 0 1012 2zm5.4 14.1c-.2.6-1.3 1.2-1.8 1.2-.5.1-1 .2-3.4-.7-2.9-1.2-4.7-4.1-4.9-4.3-.1-.2-1.2-1.6-1.2-3.1s.8-2.2 1-2.5c.3-.3.6-.4.8-.4h.6c.2 0 .4 0 .6.5s.8 1.9.8 2c.1.1.1.3 0 .5-.3.6-.6.8-.4 1.1.6 1.1 1.4 1.8 2.4 2.4.3.2.5.1.7-.1l.8-.9c.2-.3.4-.2.7-.1l2 1c.3.1.5.2.6.4 0 .1 0 .6-.5 1.5z"/></svg>
          Order via WhatsApp
        </a>
        <p v-if="site.whatsappEnabled" class="text-[11px] text-gray-400 text-center">Sends your bag as a WhatsApp message — pay on chat.</p>

        <a
          v-if="site.messengerUrl"
          :href="site.messengerUrl"
          target="_blank" rel="noopener"
          class="flex items-center justify-center gap-2 w-full text-center bg-gradient-brand text-white font-bold py-3 rounded-xl shadow hover:brightness-95 transition duration-200"
        >
          <svg class="w-5 h-5" fill="currentColor" viewBox="0 0 24 24"><path d="M20 2H4c-1.1 0-2 .9-2 2v18l4-4h14c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2z"/></svg>
          Message us on Messenger
        </a>
        <p v-if="site.messengerUrl" class="text-[11px] text-gray-400 text-center">Prefer chat? We reply fast on Facebook Messenger too.</p>
      </aside>

    </div>
  </div>
</template>

<script setup>
import { computed, onMounted } from 'vue'
import { useCartStore } from '../stores/cart'
import { useSiteStore } from '../stores/site'
import { getProductDisplayPrice } from '../utils/pricing.js'
import ExploreButton from '../components/ExploreButton.vue'

const cartStore = useCartStore()
const site = useSiteStore()

const getItemDisplayPrice = (item) =>
  getProductDisplayPrice(item.product || {}, cartStore.currentCurrency)

// Single source: store getter keeps cart + checkout totals identical.
const cartTotalDisplayPrice = computed(() => {
  const { subtotal, currency } = cartStore.cartPricing
  return `${subtotal.toFixed(2)} ${currency}`
})

const productLink = (item) => `/products/${item.product?.slug || ''}`

const lineTotal = (item) => {
  const { numeric } = getItemDisplayPrice(item)
  const total = (numeric || 0) * (item.quantity || 0)
  return `${total.toFixed(2)} ${cartStore.currentCurrency}`
}

// --- admin-managed product data surfaced in the bag ---

const sizeOptions = (item) => {
  const raw = item.product?.size_options
  return Array.isArray(raw) ? raw.filter(Boolean) : []
}

const STITCHING_LABELS = {
  unstitched: 'Unstitched',
  ready_to_wear: 'Ready to Wear',
  both: 'Stitched & Unstitched',
}
const stitchingLabel = (item) =>
  STITCHING_LABELS[item.product?.stitching_type] || ''

const stockOf = (item) => {
  const stock = item.product?.stock
  return stock == null ? null : Number(stock)
}
const isOutOfStock = (item) => stockOf(item) === 0
const isLowStock = (item) => {
  const stock = stockOf(item)
  return stock != null && stock > 0 && stock <= 3
}
const atStockCap = (item) => {
  const stock = stockOf(item)
  return stock != null && item.quantity >= stock
}
const hasOutOfStock = computed(() => cartStore.items.some(isOutOfStock))

const changeSize = (item, event) => {
  cartStore.changeSize(item.product?.id, item.size || '', event.target.value)
}

const waLines = computed(() =>
  cartStore.items.map((item) => {
    const qty = item.quantity || 0
    const unit = getItemDisplayPrice(item).numeric
    const size = item.size ? ` (${item.size})` : ''
    return `• ${qty} x ${item.product?.name}${size} — ${(unit * qty).toFixed(2)} ${cartStore.currentCurrency}`
  })
)

const whatsappCartLink = computed(() =>
  site.whatsappOrderLink(null, waLines.value, `Total: ${cartTotalDisplayPrice.value}`)
)

onMounted(() => {
  site.fetchSettings()
})
</script>
