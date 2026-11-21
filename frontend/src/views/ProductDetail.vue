<template>
  <div class="mx-auto max-w-7xl px-4 py-6 font-brand text-brand-text sm:px-6">
    <router-link to="/" class="mb-5 inline-block text-sm font-medium underline hover:text-gray-600">
      ← Back to New Arrivals
    </router-link>

    <div v-if="product" class="grid grid-cols-1 items-start gap-6 lg:grid-cols-[1.15fr_0.85fr] lg:gap-8">
      <div class="space-y-5">
        <div class="grid min-w-0 gap-3 lg:grid-cols-[76px_minmax(0,1fr)]">
          <div
            v-if="galleryItems.length > 1"
            class="order-2 flex gap-2 overflow-x-auto py-1 no-scrollbar lg:order-1 lg:flex-col lg:overflow-x-visible lg:overflow-y-auto lg:py-0"
            aria-label="Product images"
          >
            <button
              v-for="(media, index) in galleryItems"
              :key="index"
              type="button"
              :aria-label="`Show image ${index + 1} of ${galleryItems.length}`"
              :aria-pressed="index === activeMediaIndex"
              :class="index === activeMediaIndex ? 'border-black ring-1 ring-black' : 'border-gray-200 hover:border-gray-500'"
              class="h-[68px] w-[60px] shrink-0 overflow-hidden rounded-lg border-2 bg-[#f7f6f3] transition-colors sm:h-[76px] sm:w-[68px] lg:h-[84px] lg:w-full"
              @click="setActiveMedia(index)"
            >
              <video v-if="media.media_type === 'video'" :src="media.url" muted class="h-full w-full object-cover"></video>
              <img v-else :src="media.url" :alt="`${product.name} thumbnail ${index + 1}`" class="h-full w-full object-cover" />
            </button>
          </div>

          <div class="group relative order-1 min-w-0 overflow-hidden rounded-2xl bg-[#f7f6f3] ring-1 ring-black/5 lg:order-2">
            <div
              class="relative flex h-[min(68svh,620px)] min-h-[320px] items-center justify-center overflow-hidden sm:h-[min(76svh,760px)] sm:min-h-[440px] lg:h-[min(78vh,820px)]"
              @touchstart.passive="startGallerySwipe"
              @touchend.passive="finishGallerySwipe"
            >
              <template v-if="activeMedia">
                <img
                  v-if="activeMedia.media_type !== 'video'"
                  :key="'i-' + activeMediaIndex"
                  :src="activeMedia.url"
                  :alt="product.name"
                  :style="{ transformOrigin: `${zoomOrigin.x}% ${zoomOrigin.y}%` }"
                  :class="isImageZoomed ? 'scale-[2]' : ''"
                  :data-zoomed="isImageZoomed"
                  class="product-gallery-image h-full w-full cursor-zoom-in object-contain p-2 transition-transform duration-300 ease-out sm:p-4"
                  :aria-label="`${product.name} image. Activate to toggle zoom, then move to inspect details.`"
                  role="button"
                  tabindex="0"
                  @click="toggleImageZoom"
                  @pointermove="updateZoomOrigin"
                  @keydown.enter.prevent="toggleImageZoom"
                  @keydown.space.prevent="toggleImageZoom"
                />
                <video
                  v-else
                  :key="'v-' + activeMediaIndex"
                  :src="activeMedia.url"
                  controls
                  class="h-full w-full object-contain p-2 sm:p-4"
                ></video>
              </template>
              <img
                v-else
                :src="product.get_image || 'https://placehold.co/800x1000'"
                :alt="product.name"
                class="h-full w-full cursor-zoom-in object-contain p-2 sm:p-4"
                @click="toggleImageZoom"
              />

              <div class="absolute right-3 top-3 z-10 flex gap-2 sm:right-4 sm:top-4">
                <button
                  v-if="activeMedia?.media_type !== 'video'"
                  type="button"
                  class="flex h-10 w-10 items-center justify-center rounded-full bg-white/95 text-lg shadow-md ring-1 ring-black/5 transition hover:bg-white"
                  :aria-label="isImageZoomed ? 'Zoom out' : 'Zoom in'"
                  :aria-pressed="isImageZoomed"
                  @click="toggleImageZoom"
                >{{ isImageZoomed ? '−' : '+' }}</button>
                <button
                  type="button"
                  class="flex h-10 w-10 items-center justify-center rounded-full bg-white/95 shadow-md ring-1 ring-black/5 transition hover:bg-white"
                  aria-label="Open full-screen image viewer"
                  @click="openLightbox"
                >
                  <svg class="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" aria-hidden="true">
                    <path d="M8 3H5a2 2 0 0 0-2 2v3m13-5h3a2 2 0 0 1 2 2v3M3 16v3a2 2 0 0 0 2 2h3m13-5v3a2 2 0 0 1-2 2h-3" stroke-width="1.7" stroke-linecap="round" />
                  </svg>
                </button>
                <WishlistHeart
                  :product="product"
                  tip-below
                  className="w-10 h-10 border border-black/10 !bg-white shadow-md hover:!bg-gray-100 transition-all duration-200"
                />
              </div>

              <div v-if="galleryItems.length > 1" class="absolute inset-x-2 top-1/2 z-10 hidden -translate-y-1/2 justify-between px-1 sm:flex sm:px-3">
                <button
                  type="button"
                  class="flex h-10 w-10 items-center justify-center rounded-full bg-white/95 text-xl shadow-md ring-1 ring-black/5 transition hover:bg-white"
                  aria-label="Previous image"
                  @click.stop="showPreviousImage"
                >‹</button>
                <button
                  type="button"
                  class="flex h-10 w-10 items-center justify-center rounded-full bg-white/95 text-xl shadow-md ring-1 ring-black/5 transition hover:bg-white"
                  aria-label="Next image"
                  @click.stop="showNextImage"
                >›</button>
              </div>

              <div class="pointer-events-none absolute inset-x-0 bottom-0 flex items-end justify-between bg-gradient-to-t from-black/35 to-transparent px-4 pb-4 pt-12 text-white sm:px-5">
                <span class="text-xs font-medium drop-shadow">
                  <template v-if="isImageZoomed">Move image to inspect details</template>
                  <template v-else>
                    <span class="gallery-hint-touch">Tap image to zoom</span>
                    <span class="gallery-hint-pointer">Hover or tap image to zoom</span>
                  </template>
                </span>
                <span v-if="galleryItems.length > 1" class="rounded-full bg-black/35 px-2.5 py-1 text-xs tabular-nums backdrop-blur-sm">
                  {{ activeMediaIndex + 1 }} / {{ galleryItems.length }}
                </span>
              </div>
            </div>
          </div>
        </div>

        <div class="grid grid-cols-1 gap-3 sm:grid-cols-2">
          <div class="border border-black/10 p-4 bg-white">
            <h3 class="text-xs uppercase tracking-[0.16em] text-gray-500 mb-3">Select Size</h3>
            <div class="flex flex-wrap gap-2">
              <button
                v-for="size in (product.size_options || [])"
                :key="size"
                type="button"
                @click="selectedSize = size"
                :class="size === selectedSize ? 'bg-black text-white border-black' : 'bg-white text-black border-black/20 hover:border-black'"
                class="border border-black/20 rounded-none px-3 py-1.5 text-sm font-medium transition"
              >
                {{ size }}
              </button>
            </div>
            <p v-if="!product.size_options || product.size_options.length === 0" class="text-sm text-gray-500 mt-3">One size</p>
          </div>

          <div v-if="product.color_options && product.color_options.length" class="border border-black/10 p-4 bg-white">
            <h3 class="text-xs uppercase tracking-[0.16em] text-gray-500 mb-3">Select Color{{ selectedColor ? `: ${selectedColor}` : '' }}</h3>
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

          <div v-if="product.length_options && product.length_options.length" class="border border-black/10 p-4 bg-white">
            <h3 class="text-xs uppercase tracking-[0.16em] text-gray-500 mb-3">Select Length</h3>
            <div class="flex flex-wrap gap-2">
              <button
                v-for="len in product.length_options"
                :key="len"
                type="button"
                @click="selectedLength = len"
                :class="len === selectedLength ? 'bg-black text-white border-black' : 'bg-white text-black border-black/20 hover:border-black'"
                class="border border-black/20 rounded-none px-3 py-1.5 text-sm font-medium transition"
              >
                {{ len }}
              </button>
            </div>
          </div>
        </div>
      </div>

      <div class="product-meta-details space-y-4">
        <div class="border border-black/10 bg-white p-5 sm:p-6">
          <div class="mb-4">
            <h1 class="mb-2 text-2xl font-semibold tracking-tight sm:text-3xl">{{ product.name }}</h1>
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
            <div class="flex flex-wrap items-center gap-3">
              <span class="text-xl font-semibold text-black sm:text-2xl">{{ formatDisplayPrice }}</span>
              <ShareProductButton v-if="product" :product="product" class="ml-auto" />
              <span class="inline-flex border border-black/15 px-2 py-1 text-[10px] font-medium uppercase tracking-wider text-gray-600">
                {{ product.in_stock ? 'Ready to ship' : 'Sold out' }}
              </span>
            </div>
          </div>

          <p v-if="product.description" class="mb-5 text-sm leading-relaxed text-gray-600">{{ product.description }}</p>
          <p class="mb-5 flex items-center gap-2 text-sm text-gray-600">
            <span aria-hidden="true">📦</span>
            <span>Estimated delivery: {{ product.delivery_time || '20-25 days' }}</span>
          </p>

          <div class="space-y-3">
            <button
              @click="addToCart"
              :disabled="!product.in_stock || (product.size_options && product.size_options.length > 0 && !selectedSize)"
              class="w-full border border-black bg-black py-3 text-sm font-semibold text-white transition hover:bg-white hover:text-black disabled:cursor-not-allowed disabled:border-gray-300 disabled:bg-gray-300"
            >
              {{ product.in_stock ? 'Add to Cart' : 'Out of Stock' }}
            </button>
            <p v-if="product.size_options && product.size_options.length > 0 && !selectedSize" class="text-sm text-red-500">Please choose a size before adding to cart.</p>

            <a
              v-if="site.whatsappEnabled && whatsappProductLink"
              :href="whatsappProductLink"
              target="_blank"
              rel="noopener"
              class="flex w-full items-center justify-center gap-2 border border-black py-3 text-sm font-semibold text-black transition hover:bg-black hover:text-white"
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
              class="flex w-full items-center justify-center gap-2 border border-black py-3 text-sm font-semibold text-black transition hover:bg-black hover:text-white"
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

    <section v-if="relatedProducts.length" class="mt-8 border-t border-black/15 pt-6">
      <div class="mb-4 flex items-center justify-between">
        <h2 class="text-xl font-semibold tracking-tight">Related Products</h2>
        <router-link v-if="product?.category?.slug" :to="`/category/${product.category.slug}`" class="text-sm underline">View category</router-link>
      </div>
      <div class="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <ProductCard v-for="related in relatedProducts" :key="related.id" :product="related" />
      </div>
    </section>

    <div v-if="site.whatsappEnabled" class="mt-6 text-center">
      <a :href="whatsappProductLink" target="_blank" rel="noopener noreferrer"
         class="inline-flex items-center gap-2 px-5 py-2.5 rounded-full border border-emerald-600 text-emerald-700 text-sm font-medium hover:bg-emerald-50 transition">
        <svg class="w-5 h-5" fill="currentColor" viewBox="0 0 24 24"><path d="M12 2a10 10 0 00-8.6 15.1L2 22l5-1.3A10 10 0 1012 2zm5.4 14.1c-.2.6-1.3 1.2-1.8 1.2-.5.1-1 .2-3.4-.7-2.9-1.2-4.7-4.1-4.9-4.3-.1-.2-1.2-1.6-1.2-3.1s.8-2.2 1-2.5c.3-.3.6-.4.8-.4h.6c.2 0 .4 0 .6.5s.8 1.9.8 2c.1.1.1.3 0 .5-.3.6-.6.8-.4 1.1.6 1.1 1.4 1.8 2.4 2.4.3.2.5.1.7-.1l.8-.9c.2-.3.4-.2.7-.1l2 1c.3.1.5.2.6.4 0 .1 0 .6-.5 1.5z"/></svg>
        Questions about this piece? Ask us on WhatsApp
      </a>
    </div>
  </div>

  <!-- Lightbox Modal Layout -->
  <div v-if="isLightboxOpen" 
       class="fixed inset-0 z-50 flex flex-col items-center justify-center bg-black/95 p-3 backdrop-blur-md select-none sm:p-5"
       @click="isLightboxOpen = false">
    
    <div class="absolute left-4 right-4 top-4 flex items-center justify-between text-base font-medium text-white sm:left-7 sm:right-7 sm:top-6 sm:text-lg">
      <div>{{ lightboxIndex + 1 }} / {{ galleryItems.length }}</div>
      <button class="flex h-11 w-11 items-center justify-center text-4xl font-light transition hover:text-gray-300" aria-label="Close image viewer" @click="isLightboxOpen = false">
        &times;
      </button>
    </div>

    <div class="flex w-full max-w-7xl items-center justify-between gap-1 sm:gap-4" @click.stop>
      <button v-if="galleryItems.length > 1" 
              @click="prevMedia" 
              aria-label="Previous image"
              class="shrink-0 p-2 text-3xl text-white transition-colors hover:text-gray-400 sm:p-4 sm:text-5xl">
        &#10094;
      </button>
      <div v-else class="w-6 shrink-0 sm:w-16"></div>

      <div class="flex min-h-0 flex-1 items-center justify-center">
        <video v-if="currentLightboxMedia?.media_type === 'video'" 
               :src="currentLightboxMedia.url" 
               controls 
               autoplay
               class="max-h-[82vh] max-w-full object-contain shadow-2xl sm:max-h-[86vh]"></video>
        
        <img v-else 
             :src="currentLightboxMedia?.url" 
             :alt="product?.name" 
             class="max-h-[82vh] max-w-full object-contain shadow-2xl sm:max-h-[86vh]" />
      </div>

      <button v-if="galleryItems.length > 1" 
              @click="nextMedia" 
              aria-label="Next image"
              class="shrink-0 p-2 text-3xl text-white transition-colors hover:text-gray-400 sm:p-4 sm:text-5xl">
        &#10095;
      </button>
      <div v-else class="w-6 shrink-0 sm:w-16"></div>
    </div>

    <div v-if="galleryItems.length > 1" class="mt-4 flex max-w-full gap-2 overflow-x-auto p-2 no-scrollbar sm:mt-6" @click.stop>
      <button v-for="(med, idx) in galleryItems" 
              :key="'lb-'+idx" 
              @click="setActiveMedia(idx)"
              :aria-label="`Show image ${idx + 1} of ${galleryItems.length}`"
              :aria-pressed="idx === lightboxIndex"
              :class="idx === lightboxIndex ? 'border-white scale-105 opacity-100' : 'border-transparent opacity-50'"
              class="h-14 w-14 shrink-0 overflow-hidden border-2 bg-neutral-900 transition-all duration-200 sm:h-16 sm:w-16">
        <video v-if="med.media_type === 'video'" :src="med.url" muted class="w-full h-full object-cover"></video>
        <img v-else :src="med.url" class="w-full h-full object-cover" />
      </button>
    </div>
  </div>
</template>

<style scoped>
@media (hover: hover) and (pointer: fine) {
  .gallery-hint-touch {
    display: none;
  }
  .gallery-hint-pointer {
    display: inline;
  }
  .product-gallery-image:not([data-zoomed='true']):hover {
    scale: 1.65;
  }
}

@media (hover: none), (pointer: coarse) {
  .gallery-hint-pointer {
    display: none;
  }
}

.product-gallery-image[data-zoomed='true'] {
  transition-duration: 80ms;
}
</style>

<script setup>
import { ref, onMounted, computed, onBeforeUnmount, watch } from 'vue'
import { useRoute } from 'vue-router'
import axios from 'axios'
import { useCartStore } from '../stores/cart'
import { useSiteStore } from '../stores/site'
import ProductReviews from '../components/ProductReviews.vue'
import WishlistHeart from '../components/WishlistHeart.vue'
import ProductCard from '../components/ProductCard.vue'
import ShareProductButton from '../components/ShareProductButton.vue'
import { formatProductPrice } from '../utils/pricing.js'

// 1. Core States defined first
const product = ref(null)
const relatedProducts = ref([])
const selectedSize = ref('')
const selectedColor = ref('')
const selectedLength = ref('')
const showSuccessMessage = ref(false)

const activeMediaIndex = ref(0)
const isLightboxOpen = ref(false)
const lightboxIndex = ref(0)
const zoomOrigin = ref({ x: 50, y: 50 })
const isImageZoomed = ref(false)
const swipeStartX = ref(null)

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
      fetchRelatedProducts(response.data.category?.slug, response.data.id)
    } else {
      product.value = null
      relatedProducts.value = []
      console.warn("API returned invalid payload format")
    }
  } catch (error) {
    console.error('CRITICAL: API Fetch failed details:', {
      status: error.response?.status,
      data: error.response?.data,
      message: error.message
    })
    product.value = null
    relatedProducts.value = []
  }
}

const fetchRelatedProducts = async (categorySlug, productId) => {
  if (!categorySlug) {
    relatedProducts.value = []
    return
  }
  try {
    const response = await axios.get(`/api/v1/products/?category=${encodeURIComponent(categorySlug)}`)
    const items = Array.isArray(response.data) ? response.data : (response.data.results || response.data.products || [])
    relatedProducts.value = items.filter((item) => item.id !== productId).slice(0, 4)
  } catch (error) {
    console.error('Related products could not be loaded:', error)
    relatedProducts.value = []
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
  activeMediaIndex.value = 0
  lightboxIndex.value = 0
  isLightboxOpen.value = false
  isImageZoomed.value = false
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
  lightboxIndex.value = index
  isImageZoomed.value = false
  zoomOrigin.value = { x: 50, y: 50 }
}

function updateZoomOrigin(event) {
  const bounds = event.currentTarget.parentElement.getBoundingClientRect()
  zoomOrigin.value = {
    x: Math.max(0, Math.min(100, ((event.clientX - bounds.left) / bounds.width) * 100)),
    y: Math.max(0, Math.min(100, ((event.clientY - bounds.top) / bounds.height) * 100)),
  }
}

function toggleImageZoom() {
  if (activeMedia.value?.media_type === 'video') return
  isImageZoomed.value = !isImageZoomed.value
  if (!isImageZoomed.value) zoomOrigin.value = { x: 50, y: 50 }
}

function startGallerySwipe(event) {
  swipeStartX.value = event.changedTouches[0]?.clientX ?? null
}

function finishGallerySwipe(event) {
  const endX = event.changedTouches[0]?.clientX
  if (swipeStartX.value === null || endX === undefined || isImageZoomed.value) {
    swipeStartX.value = null
    return
  }
  const distance = endX - swipeStartX.value
  if (Math.abs(distance) > 48) {
    if (distance < 0) showNextImage()
    else showPreviousImage()
  }
  swipeStartX.value = null
}

function showNextImage() {
  setActiveMedia((activeMediaIndex.value + 1) % galleryItems.value.length)
}

function showPreviousImage() {
  setActiveMedia((activeMediaIndex.value - 1 + galleryItems.value.length) % galleryItems.value.length)
}

function openLightbox() {
  lightboxIndex.value = activeMediaIndex.value
  isImageZoomed.value = false
  isLightboxOpen.value = true
}

function nextMedia() {
  showNextImage()
}

function prevMedia() {
  showPreviousImage()
}

function handleKeyDown(e) {
  if (!isLightboxOpen.value) return
  if (e.key === 'ArrowRight') nextMedia()
  if (e.key === 'ArrowLeft') prevMedia()
  if (e.key === 'Escape') isLightboxOpen.value = false
}

// 4. Reactive Price Formatter with Cross-Currency Conversion Fallback
const formatDisplayPrice = computed(() => {
  return product.value ? formatProductPrice(product.value, cartStore.currentCurrency) : '0.00'
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