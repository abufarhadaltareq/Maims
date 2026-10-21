<template>
  <div class="product-card group relative flex flex-col bg-white rounded-2xl overflow-hidden border border-gray-100 hover:border-gray-200 hover:shadow-[0_16px_40px_-16px_rgba(15,23,42,0.25)] hover:-translate-y-1 transition-all duration-300">
    <!-- Image with badges + hover actions -->
    <router-link
      :to="`/products/${product.slug}`"
      class="block relative overflow-hidden bg-brand-muted aspect-[3/4]"
    >
      <img
        :src="product.get_thumbnail || product.get_image || 'https://placehold.co/400x533'"
        class="w-full h-full object-cover group-hover:scale-[1.06] transition duration-500 ease-out"
        :alt="product.name"
        loading="lazy"
      />
      <!-- Badges -->
      <div class="absolute top-2.5 left-2.5 flex flex-col gap-1.5">
        <span v-if="isNew" class="text-[10px] font-extrabold uppercase tracking-wider bg-[var(--color-brand)] text-white px-2.5 py-1 rounded-full shadow">New</span>
        <span v-if="isSocial" class="text-[10px] font-extrabold uppercase tracking-wider bg-[#1877F2] text-white px-2.5 py-1 rounded-full shadow flex items-center gap-1">
          <span class="w-1.5 h-1.5 rounded-full bg-white animate-pulse"></span> Live
        </span>
        <span v-if="!product.in_stock" class="text-[10px] font-extrabold uppercase tracking-wider bg-white/90 backdrop-blur text-gray-700 px-2.5 py-1 rounded-full shadow">Sold out</span>
      </div>
      <span v-if="discountPct" class="absolute top-2.5 right-2.5 text-[10px] font-extrabold bg-rose-600 text-white px-2.5 py-1 rounded-full shadow">-{{ discountPct }}%</span>
      <!-- Hover quick actions. @click.stop keeps every action inside from
           bubbling into the card's router-link (which would navigate away
           mid-click instead of just toggling the heart / adding to bag). -->
      <div @click.stop class="absolute inset-x-2.5 bottom-2.5 flex gap-2 items-center translate-y-16 opacity-0 group-hover:translate-y-0 group-hover:opacity-100 transition-all duration-300">
        <button
          @click.prevent="onAdd"
          :disabled="!product.in_stock"
          class="flex-1 min-h-[44px] text-[11px] font-bold uppercase tracking-wider bg-gradient-brand text-white py-2.5 rounded-xl shadow hover:brightness-105 transition active:scale-95 disabled:opacity-40 items-center justify-center"
        >
          {{ product.in_stock ? (hasSizes ? 'Pick size' : 'Quick add') : 'Sold out' }}
        </button>
        <WishlistHeart :product="product" class="flex-shrink-0" />
      </div>
    </router-link>

    <div class="flex flex-col flex-1 p-3.5">
      <p v-if="product.brand_name" class="text-[10px] uppercase tracking-[0.18em] text-[var(--color-content-secondary)] font-bold mb-1 truncate">{{ product.brand_name }}</p>
      <router-link :to="`/products/${product.slug}`" class="font-semibold text-[14px] leading-snug line-clamp-2 group-hover:text-brand-accent transition-colors min-h-[2.6em]">{{ product.name }}</router-link>
      <!-- Rating -->
      <div class="flex items-center gap-1 mt-1.5">
        <span class="flex text-[13px] leading-none" aria-label="rating">
          <span v-for="i in 5" :key="i" :class="i <= roundedRating ? 'text-amber-400' : 'text-gray-200'">★</span>
        </span>
        <span v-if="reviewCount" class="text-[11px] text-[var(--color-content-secondary)] font-medium">({{ reviewCount }})</span>
        <span v-else class="text-[11px] text-[var(--color-content-secondary)] font-medium">No reviews</span>
      </div>
      <div class="flex flex-wrap items-center gap-2 mt-1.5">
        <p class="text-[var(--color-content)] font-extrabold text-[15px]">{{ priceString }}</p>
        <p v-if="compareAt" class="text-[var(--color-content-secondary)] text-xs line-through font-medium">{{ compareAt }}</p>
        <ShareProductButton :product="product" class="ml-auto" />
      </div>

      <!-- Mobile / keyboard fallback add (hover bar is desktop-only) -->
      <div class="mt-2.5 md:hidden">
        <button
          v-if="!pickerOpen"
          @click="onAdd"
          :disabled="!product.in_stock"
          class="w-full rounded-xl bg-[var(--color-brand)] text-white text-xs font-bold py-2.5 transition active:scale-95 disabled:opacity-40"
        >
          {{ product.in_stock ? (hasSizes ? 'Select size' : 'Add to Cart') : 'Out of Stock' }}
        </button>
        <div v-else class="flex flex-wrap gap-1.5">
          <button
            v-for="size in product.size_options"
            :key="size"
            @click="addWithSize(size)"
            class="rounded-full border border-gray-200 bg-white text-xs font-bold px-3 py-1.5 transition hover:border-[var(--color-brand)] active:scale-95"
          >
            {{ size }}
          </button>
        </div>
      </div>
      <!-- Desktop size picker expansion -->
      <div v-if="pickerOpen" class="hidden md:flex flex-wrap gap-1.5 mt-2.5">
        <button
          v-for="size in product.size_options"
          :key="size"
          @click="addWithSize(size)"
          class="rounded-full border border-gray-200 bg-white text-xs font-bold px-3 py-1.5 transition hover:border-[var(--color-brand)] hover:bg-gray-50 active:scale-95"
        >
          {{ size }}
        </button>
      </div>
      <p v-if="added" class="text-emerald-600 text-xs font-bold mt-1.5 flex items-center gap-1">
        <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" stroke-width="2.5" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M4.5 12.75l6 6 9-13.5"/></svg>
        Added to bag{{ lastSize ? ` — ${lastSize}` : '' }}
      </p>
    </div>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import { useCartStore } from '../stores/cart'
import { getProductDisplayPrice } from '../utils/pricing.js'
import WishlistHeart from './WishlistHeart.vue'
import ShareProductButton from './ShareProductButton.vue'

const props = defineProps({
  product: { type: Object, required: true },
  currency: { type: String, default: '' },
})

const cartStore = useCartStore()
const pickerOpen = ref(false)
const added = ref(false)
const lastSize = ref('')
let addedTimer = null

const hasSizes = computed(() =>
  Array.isArray(props.product.size_options) && props.product.size_options.length > 0
)

const activeCurrency = computed(() => props.currency || cartStore.currentCurrency)

const priceString = computed(() =>
  getProductDisplayPrice(props.product || {}, activeCurrency.value).string
)

// Compare-at price (sale badge) — supported when backend sends `compare_at_price` or `original_price`.
const compareAt = computed(() => {
  const raw = props.product.compare_at_price ?? props.product.original_price ?? null
  if (!raw || Number(raw) <= 0) return ''
  const sell = getProductDisplayPrice(props.product || {}, activeCurrency.value).numeric || 0
  if (Number(raw) <= sell) return ''
  return `${Number(raw).toFixed(2)} ${activeCurrency.value}`
})

const discountPct = computed(() => {
  const raw = props.product.compare_at_price ?? props.product.original_price ?? null
  if (!raw || Number(raw) <= 0) return 0
  const sell = getProductDisplayPrice(props.product || {}, activeCurrency.value).numeric || 0
  if (!sell || Number(raw) <= sell) return 0
  return Math.round((1 - sell / Number(raw)) * 100)
})

const roundedRating = computed(() => Math.round(Number(props.product.average_rating || 0)))
const reviewCount = computed(() => Number(props.product.review_count || 0))

// "New" = added in the last 21 days. "Live" = synced from the Facebook Page.
const isNew = computed(() => {
  if (!props.product.date_added) return false
  const addedAt = new Date(props.product.date_added).getTime()
  if (Number.isNaN(addedAt)) return false
  return Date.now() - addedAt < 21 * 24 * 3600 * 1000
})
const isSocial = computed(() => !!(props.product.facebook_post_id || props.product.facebook_image_url))

function flashAdded(size = '') {
  lastSize.value = size
  added.value = true
  clearTimeout(addedTimer)
  addedTimer = setTimeout(() => { added.value = false }, 2000)
}

function onAdd() {
  if (!props.product.in_stock) return
  if (hasSizes.value) {
    pickerOpen.value = !pickerOpen.value
    return
  }
  cartStore.addToCart(props.product, '', 1)
  flashAdded('')
}

function addWithSize(size) {
  cartStore.addToCart(props.product, size, 1)
  pickerOpen.value = false
  flashAdded(size)
}
</script>
