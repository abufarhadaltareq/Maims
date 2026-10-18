<template>
  <div class="py-10 px-8 max-w-7xl mx-auto font-brand text-brand-text">
    <router-link to="/" class="inline-block mb-8 text-sm font-semibold underline hover:text-gray-600">
      ← Back to New Arrivals
    </router-link>

    <div v-if="product" class="grid grid-cols-1 lg:grid-cols-[1.4fr_1fr] gap-12 items-start">
      <div class="space-y-8">
        <div class="relative rounded-[2rem] overflow-hidden shadow-2xl shadow-slate-300/40 transform-gpu hover:-translate-y-1 transition-all duration-500 bg-white">
          <WishlistHeart
            :product="product"
            tip-below
            className="absolute top-4 right-4 z-10 w-10 h-10 sm:w-12 sm:h-12 border-2 border-white !bg-white shadow-lg shadow-slate-900/25 hover:!bg-white/90 hover:!scale-110 transition-all duration-200"
          />
          
          <div class="h-[640px] sm:h-[760px] lg:h-[880px] bg-[var(--color-brand)]/5 flex items-center justify-center overflow-hidden cursor-zoom-in group" @click="openLightbox">
            <template v-if="activeMedia">
              <video v-if="activeMedia.media_type === 'video'" :key="'v-' + activeMediaIndex" :src="activeMedia.url" controls class="w-full h-full object-cover animate-media-switch" @click.stop></video>
              <img v-else :key="'i-' + activeMediaIndex" :src="activeMedia.url" :alt="product.name" class="w-full h-full object-cover animate-media-switch transition-transform duration-700 group-hover:scale-105" />
            </template>
            <template v-else>
              <img :src="product.get_image || 'https://placehold.co/600x800'" :alt="product.name" class="w-full h-full object-cover" />
            </template>
          </div>

          <div v-if="galleryItems.length > 1" class="absolute bottom-4 left-4 right-4 flex gap-3 overflow-x-auto no-scrollbar">
            <button
              v-for="(media, index) in galleryItems"
              :key="index"
              @click.stop="setActiveMedia(index)"
              type="button"
              :class="index === activeMediaIndex ? 'border-black scale-95 shadow-inner' : 'border-white/80'"
              class="min-w-[96px] h-24 rounded-3xl border-2 bg-white/90 shadow-lg overflow-hidden transition-all duration-300 hover:-translate-y-1"
            >
              <video v-if="media.media_type === 'video'" :src="media.url" muted class="w-full h-full object-cover"></video>
              <img v-else :src="media.url" class="w-full h-full object-cover" />
            </button>
          </div>
        </div>

        <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div class="rounded-3xl border border-gray-100 p-4 bg-white shadow-sm">
            <h3 class="text-sm uppercase tracking-[0.3em] text-gray-400 mb-3">Availability</h3>
            <p class="text-lg font-bold text-purple-900">{{ product.in_stock ? 'In Stock' : 'Out of Stock' }}</p>
            <p class="text-sm text-gray-500 mt-1">{{ product.stock }} unit{{ product.stock === 1 ? '' : 's' }} available</p>
          </div>

          <div class="rounded-3xl border border-gray-100 p-4 bg-white shadow-sm">
            <h3 class="text-sm uppercase tracking-[0.3em] text-gray-400 mb-3">Select Size</h3>
            <div class="flex flex-wrap gap-2">
              <button
                v-for="size in (product.size_options || [])"
                :key="size"
                type="button"
                @click="selectedSize = size"
                :class="size === selectedSize ? 'bg-gradient-brand text-white border-transparent' : 'bg-white text-purple-700 border-purple-200 hover:border-purple-400'"
                class="border rounded px-3.5 py-2 text-sm font-semibold transition"
              >
                {{ size }}
              </button>
            </div>
            <p v-if="!product.size_options || product.size_options.length === 0" class="text-sm text-gray-500 mt-3">One size / no size options for this item.</p>
          </div>

          <div v-if="product.color_options && product.color_options.length" class="rounded-3xl border border-gray-100 p-4 bg-white shadow-sm">
            <h3 class="text-sm uppercase tracking-[0.3em] text-gray-400 mb-3">Select Color{{ selectedColor ? `: ${selectedColor}` : '' }}</h3>
            <div class="flex flex-wrap gap-2.5">
              <button
                v-for="color in product.color_options"
                :key="color"
                type="button"
                @click="selectedColor = color"
                :title="color"
                :aria-label="`Choose ${color}`"
                :style="{ backgroundColor: colorSwatch(color) }"
                :class="color === selectedColor ? 'ring-2 ring-offset-2 ring-black scale-110' : 'ring-1 ring-black/15 hover:scale-110'"
                class="w-9 h-9 rounded-full transition-transform"
              />
            </div>
          </div>

          <div v-if="product.length_options && product.length_options.length" class="rounded-3xl border border-gray-100 p-4 bg-white shadow-sm">
            <h3 class="text-sm uppercase tracking-[0.3em] text-gray-400 mb-3">Select Length</h3>
            <div class="flex flex-wrap gap-2">
              <button
                v-for="len in product.length_options"
                :key="len"
                type="button"
                @click="selectedLength = len"
                :class="len === selectedLength ? 'bg-gradient-brand text-white border-transparent' : 'bg-white text-purple-700 border-purple-200 hover:border-purple-400'"
                class="border rounded px-3.5 py-2 text-sm font-semibold transition"
              >
                {{ len }}
              </button>
            </div>
          </div>
        </div>
      </div>

      <div class="product-meta-details space-y-6">
        <div class="rounded-[2rem] border border-gray-100 bg-white p-8 shadow-lg shadow-slate-200/50">
          <div class="mb-6">
            <h1 class="text-5xl font-extrabold tracking-tight mb-3">{{ product.name }}</h1>
            <!-- Star rating summary. Jumps to the reviews section below. -->
            <a
              v-if="product.review_count"
              href="#reviews"
              class="inline-flex items-center gap-1.5 mb-3 text-sm text-gray-500 hover:text-brand-primary transition"
            >
              <span class="flex gap-0.5" aria-hidden="true">
                <span
                  v-for="star in 5"
                  :key="star"
                  class="text-sm"
                  :class="star <= Math.round(product.average_rating || 0) ? 'text-amber-400' : 'text-gray-200'"
                >★</span>
              </span>
              <span>{{ Number(product.average_rating).toFixed(1) }} ({{ product.review_count }})</span>
            </a>
            <div class="flex items-center gap-3">
              <span class="text-4xl font-black text-brand-accent">{{ formatDisplayPrice }}</span>
              <span class="inline-flex rounded-full border border-slate-200 px-3 py-1 text-xs font-semibold uppercase tracking-[0.25em] text-slate-500">
                {{ product.in_stock ? 'Ready to ship' : 'Sold out' }}
              </span>
            </div>
          </div>

          <div class="space-y-4 mb-6">
            <p class="text-slate-600 leading-relaxed">{{ product.description || 'A refined product with premium design and visuals.' }}</p>
            <div class="grid grid-cols-2 gap-3 text-sm text-slate-500">
              <div class="rounded-3xl bg-slate-50 p-4">
                <span class="block uppercase tracking-[0.22em] font-semibold">Category</span>
                <span class="block mt-2 text-slate-800">{{ product.category?.name || 'Unassigned' }}</span>
              </div>
              <div class="rounded-3xl bg-slate-50 p-4">
                <span class="block uppercase tracking-[0.22em] font-semibold">Added</span>
                <span class="block mt-2 text-slate-800">{{ product.date_added ? new Date(product.date_added).toLocaleDateString() : 'N/A' }}</span>
              </div>
            </div>
          </div>

          <div class="space-y-4">
            <button
              @click="addToCart"
              :disabled="!product.in_stock || (product.size_options && product.size_options.length > 0 && !selectedSize)"
              class="w-full rounded-full py-4 text-lg font-bold transition shadow-lg text-white bg-gradient-brand hover:brightness-105 disabled:cursor-not-allowed disabled:bg-gray-300"
            >
              {{ product.in_stock ? 'Add to Cart' : 'Out of Stock' }}
            </button>
            <p v-if="product.size_options && product.size_options.length > 0 && !selectedSize" class="text-sm text-red-500">Please choose a size before adding to cart.</p>

            <a
              v-if="site.whatsappEnabled && whatsappProductLink"
              :href="whatsappProductLink"
              target="_blank"
              rel="noopener"
              class="flex items-center justify-center gap-2 w-full rounded-full py-4 text-lg font-bold transition shadow-lg text-white bg-gradient-brand hover:brightness-95"
            >
              <svg class="w-5 h-5" fill="currentColor" viewBox="0 0 24 24"><path d="M12 2a10 10 0 00-8.6 15.1L2 22l5-1.3A10 10 0 1012 2zm5.4 14.1c-.2.6-1.3 1.2-1.8 1.2-.5.1-1 .2-3.4-.7-2.9-1.2-4.7-4.1-4.9-4.3-.1-.2-1.2-1.6-1.2-3.1s.8-2.2 1-2.5c.3-.3.6-.4.8-.4h.6c.2 0 .4 0 .6.5s.8 1.9.8 2c.1.1.1.3 0 .5-.3.6-.6.8-.4 1.1.6 1.1 1.4 1.8 2.4 2.4.3.2.5.1.7-.1l.8-.9c.2-.3.4-.2.7-.1l2 1c.3.1.5.2.6.4 0 .1 0 .6-.5 1.5z"/></svg>
              Order via WhatsApp
            </a>
            <p v-if="site.whatsappEnabled" class="text-xs text-gray-400 text-center">Questions or pay-on-chat orders — we reply fast on WhatsApp.</p>

            <a
              v-if="site.messengerUrl"
              :href="site.messengerUrl"
              target="_blank"
              rel="noopener"
              class="flex items-center justify-center gap-2 w-full rounded-full py-4 text-lg font-bold transition shadow-lg text-white bg-gradient-brand hover:brightness-95"
            >
              <svg class="w-5 h-5" fill="currentColor" viewBox="0 0 24 24"><path d="M20 2H4c-1.1 0-2 .9-2 2v18l4-4h14c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2z"/></svg>
              Message us on Messenger
            </a>
            <p v-if="site.messengerUrl" class="text-xs text-gray-400 text-center">Prefer chat? We reply fast on Facebook Messenger too.</p>
          </div>

          <p v-if="showSuccessMessage" class="mt-4 text-emerald-600 font-semibold flex items-center gap-2">
            ✓ Added to bag with size {{ selectedSize || 'Standard' }}.
          </p>
        </div>
      </div>
    </div>

    <div v-else class="text-center py-12 text-gray-400 font-medium">
      <p>Loading premium product details...</p>
    </div>

    <!-- Star rating + reviews. Only rendered once the product exists, since the
         component keys its requests off the slug. -->
    <ProductReviews v-if="product" :product-slug="product.slug" />

    <div v-if="site.whatsappEnabled" class="mt-10 text-center">
      <a :href="whatsappProductLink" target="_blank" rel="noopener noreferrer"
         class="inline-flex items-center gap-2 px-5 py-2.5 rounded-full border border-emerald-600 text-emerald-700 text-sm font-medium hover:bg-emerald-50 transition">
        <svg class="w-5 h-5" fill="currentColor" viewBox="0 0 24 24"><path d="M12 2a10 10 0 00-8.6 15.1L2 22l5-1.3A10 10 0 1012 2zm5.4 14.1c-.2.6-1.3 1.2-1.8 1.2-.5.1-1 .2-3.4-.7-2.9-1.2-4.7-4.1-4.9-4.3-.1-.2-1.2-1.6-1.2-3.1s.8-2.2 1-2.5c.3-.3.6-.4.8-.4h.6c.2 0 .4 0 .6.5s.8 1.9.8 2c.1.1.1.3 0 .5-.3.6-.6.8-.4 1.1.6 1.1 1.4 1.8 2.4 2.4.3.2.5.1.7-.1l.8-.9c.2-.3.4-.2.7-.1l2 1c.3.1.5.2.6.4 0 .1 0 .6-.5 1.5z"/></svg>
        Questions about this piece? Ask us on WhatsApp
      </a>
    </div>
  </div>

  <!-- Lightbox Modal Layout -->
  <div v-if="isLightboxOpen" 
       class="fixed inset-0 z-50 bg-[var(--color-brand)]/95 flex flex-col items-center justify-center p-4 backdrop-blur-md select-none"
       @click="isLightboxOpen = false">
    
    <div class="absolute top-6 left-6 right-6 flex justify-between items-center text-white text-lg font-medium">
      <div>{{ lightboxIndex + 1 }} / {{ galleryItems.length }}</div>
      <button class="text-5xl font-light hover:text-gray-300 transition" @click="isLightboxOpen = false">
        &times;
      </button>
    </div>

    <div class="w-full max-w-5xl flex items-center justify-between gap-4" @click.stop>
      <button v-if="galleryItems.length > 1" 
              @click="prevMedia" 
              class="text-white text-5xl hover:text-gray-400 transition-colors p-4 select-none">
        &#10094;
      </button>
      <div v-else class="w-16"></div>

      <div class="flex-1 flex justify-center items-center max-h-[88vh]">
        <video v-if="currentLightboxMedia?.media_type === 'video'" 
               :src="currentLightboxMedia.url" 
               controls 
               autoplay
               class="max-w-full max-h-[88vh] object-contain rounded-xl shadow-2xl"></video>
        
        <img v-else 
             :src="currentLightboxMedia?.url" 
             :alt="product?.name" 
             class="max-w-full max-h-[88vh] object-contain rounded-xl shadow-2xl" />
      </div>

      <button v-if="galleryItems.length > 1" 
              @click="nextMedia" 
              class="text-white text-5xl hover:text-gray-400 transition-colors p-4 select-none">
        &#10095;
      </button>
      <div v-else class="w-16"></div>
    </div>

    <div v-if="galleryItems.length > 1" class="mt-6 flex gap-2 overflow-x-auto p-2 max-w-2xl no-scrollbar" @click.stop>
      <button v-for="(med, idx) in galleryItems" 
              :key="'lb-'+idx" 
              @click="lightboxIndex = idx"
              :class="idx === lightboxIndex ? 'border-white scale-105 opacity-100' : 'border-transparent opacity-50'"
              class="w-16 h-16 rounded-xl overflow-hidden border-2 transition-all duration-200 bg-neutral-900 flex-shrink-0">
        <video v-if="med.media_type === 'video'" :src="med.url" muted class="w-full h-full object-cover"></video>
        <img v-else :src="med.url" class="w-full h-full object-cover" />
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, computed, onBeforeUnmount, watch } from 'vue'
import { useRoute } from 'vue-router'
import axios from 'axios'
import { useCartStore } from '../stores/cart'
import { useSiteStore } from '../stores/site'
import ProductReviews from '../components/ProductReviews.vue'
import WishlistHeart from '../components/WishlistHeart.vue'

// 1. Core States defined first
const product = ref(null)
const selectedSize = ref('')
const selectedColor = ref('')
const selectedLength = ref('')
const showSuccessMessage = ref(false)

const activeMediaIndex = ref(0)
const isLightboxOpen = ref(false)
const lightboxIndex = ref(0)

const route = useRoute()
const cartStore = useCartStore()
const site = useSiteStore()

// WhatsApp order link prefilled with this product + selected variant
const whatsappProductLink = computed(() => {
  if (!product.value) return ''
  const parts = []
  if (selectedSize.value) parts.push(`Size: ${selectedSize.value}`)
  if (selectedColor.value) parts.push(`Color: ${selectedColor.value}`)
  if (selectedLength.value) parts.push(`Length: ${selectedLength.value}`)
  const variant = parts.length ? ` (${parts.join(', ')})` : ''
  const price = formatDisplayPrice.value
  return site.whatsappOrderLink(
    null,
    [`• 1 x ${product.value.name}${variant} — ${price}`],
    `Product: ${window.location.origin}/products/${route.params.slug}`
  )
})

const COLOR_HEX = {
  red: '#e11d48', maroon: '#7A1F1F', pink: '#f9a8d4', black: '#111111',
  white: '#ffffff', ivory: '#fffff0', beige: '#f5f5dc', cream: '#fffdd0',
  green: '#16a34a', emerald: '#059669', olive: '#808000', mint: '#a7f3d0',
  blue: '#2563eb', navy: '#1e3a8a', sky: '#87ceeb', teal: '#0d9488',
  yellow: '#facc15', gold: '#d4af37', mustard: '#e1ad01', orange: '#f97316',
  purple: '#9333ea', lavender: '#e6e6fa', magenta: '#ff00ff', burgundy: '#800020',
  brown: '#92400e', grey: '#808080', gray: '#808080', silver: '#c0c0c0',
}
const colorSwatch = (name) => {
  const v = String(name || '').trim()
  if (/^#([0-9a-f]{3}|[0-9a-f]{6})$/i.test(v)) return v
  return COLOR_HEX[v.toLowerCase()] || '#d1d5db'
}

// 2. Fetch API Data
const fetchProductData = async () => {
  const slug = route.params.slug
  if (!slug) return
  
  try {
    const response = await axios.get(`/api/v1/products/${slug}/`)
    console.log("Raw Product API payload:", response.data)
    
    if (response.data && typeof response.data === 'object') {
      product.value = response.data
    } else {
      product.value = null
      console.warn("API returned invalid payload format")
    }
  } catch (error) {
    console.error('CRITICAL: API Fetch failed details:', {
      status: error.response?.status,
      data: error.response?.data,
      message: error.message
    })
    product.value = null
  }
}

onMounted(() => {
  fetchProductData()
  site.fetchSettings()
  window.addEventListener('keydown', handleKeyDown)
})

onBeforeUnmount(() => {
  window.removeEventListener('keydown', handleKeyDown)
})

watch(() => route.params.slug, () => {
  product.value = null
  fetchProductData()
})

// 3. Media Gallery Computeds
const galleryItems = computed(() => {
  const itemsList = []
  if (product.value?.get_image) {
    itemsList.push({
      id: 'primary-image',
      media_type: 'image',
      url: product.value.get_image
    })
  }
  if (product.value?.media && product.value.media.length > 0) {
    product.value.media.forEach(item => {
      if (item.url !== product.value.get_image) {
        itemsList.push(item)
      }
    })
  }
  if (itemsList.length === 0) {
    itemsList.push({
      id: 'placeholder',
      media_type: 'image',
      url: 'https://placehold.co/600x800'
    })
  }
  return itemsList
})

const activeMedia = computed(() => galleryItems.value[activeMediaIndex.value] || null)
const currentLightboxMedia = computed(() => galleryItems.value[lightboxIndex.value] || null)

function setActiveMedia(index) {
  activeMediaIndex.value = index
}

function openLightbox() {
  lightboxIndex.value = activeMediaIndex.value
  isLightboxOpen.value = true
}

function nextMedia() {
  lightboxIndex.value = (lightboxIndex.value + 1) % galleryItems.value.length
}

function prevMedia() {
  lightboxIndex.value = (lightboxIndex.value - 1 + galleryItems.value.length) % galleryItems.value.length
}

function handleKeyDown(e) {
  if (!isLightboxOpen.value) return
  if (e.key === 'ArrowRight') nextMedia()
  if (e.key === 'ArrowLeft') prevMedia()
  if (e.key === 'Escape') isLightboxOpen.value = false
}

// 4. Reactive Price Formatter with Cross-Currency Conversion Fallback
const formatDisplayPrice = computed(() => {
  if (!product.value) return '0.00'
  
  const selectedCurrency = cartStore.currentCurrency
  
  // Try exact database record match for the chosen currency
  const regionalPrice = product.value.prices?.find(p => p.currency === selectedCurrency)
  if (regionalPrice) {
    return `${Number(regionalPrice.price).toFixed(2)} ${selectedCurrency}`
  }
  
  // Conversion Fallback Strategy if exact currency node is missing
  const backupPriceObj = product.value.prices?.[0]
  if (backupPriceObj) {
    const basePrice = Number(backupPriceObj.price)
    const baseCurrency = backupPriceObj.currency
    
    // Core currency index conversion rates
    const ratesToUSD = {
      'SEK': 0.095,
      'PKR': 0.0036,
      'EUR': 1.08,
      'BDT': 0.0085,
      'USD': 1.0
    }
    
    const rateInUSD = ratesToUSD[baseCurrency] || 1.0
    const targetRateFromUSD = ratesToUSD[selectedCurrency] || 1.0
    
    const convertedPrice = (basePrice * rateInUSD) / targetRateFromUSD
    return `${convertedPrice.toFixed(2)} ${selectedCurrency}`
  }
  
  return `${Number(product.value.price || 0).toFixed(2)} ${selectedCurrency}`
})

const hasSizeSelection = computed(() => {
  return Array.isArray(product.value?.size_options) && product.value.size_options.length > 0
})

function addToCart() {
  if (!product.value) return
  if (hasSizeSelection.value && !selectedSize.value) return

  // Extract current dynamic price string back to a valid numeric structure for the cart schema
  const currentPriceString = formatDisplayPrice.value.split(' ')[0]
  const parsedPrice = parseFloat(currentPriceString) || 0

  // Variant travels as "size | color | length" so each combination is its own bag line.
  const variant = [selectedSize.value, selectedColor.value, selectedLength.value]
    .filter(Boolean).join(' | ')

  cartStore.addToCart({
    ...product.value,
    price: parsedPrice
  }, selectedSize.value, 1, variant)

  showSuccessMessage.value = true
  setTimeout(() => {
    showSuccessMessage.value = false
  }, 2000)
}
</script>