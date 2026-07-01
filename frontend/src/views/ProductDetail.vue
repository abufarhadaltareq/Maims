<template>
  <div class="py-10 px-8 max-w-7xl mx-auto font-brand text-brand-text">
    <router-link to="/" class="inline-block mb-8 text-sm font-semibold underline hover:text-gray-600">
      ← Back to New Arrivals
    </router-link>

    <div v-if="product" class="grid grid-cols-1 lg:grid-cols-[1.4fr_1fr] gap-12 items-start">
      <div class="space-y-8">
        <div class="relative rounded-[2rem] overflow-hidden shadow-2xl shadow-slate-300/40 transform-gpu hover:-translate-y-1 transition-all duration-500 bg-white">
          
          <div class="h-[520px] bg-slate-900/5 flex items-center justify-center overflow-hidden cursor-zoom-in" @click="openLightbox">
            <template v-if="activeMedia">
              <video v-if="activeMedia.media_type === 'video'" :src="activeMedia.url" controls class="w-full h-full object-cover" @click.stop></video>
              <img v-else :src="activeMedia.url" :alt="product.name" class="w-full h-full object-cover" />
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
            <p class="text-lg font-bold text-slate-900">{{ product.in_stock ? 'In Stock' : 'Out of Stock' }}</p>
            <p class="text-sm text-gray-500 mt-1">{{ product.stock }} unit{{ product.stock === 1 ? '' : 's' }} available</p>
          </div>

          <div class="rounded-3xl border border-gray-100 p-4 bg-white shadow-sm">
            <h3 class="text-sm uppercase tracking-[0.3em] text-gray-400 mb-3">Select Size</h3>
            <div class="flex flex-wrap gap-3">
              <button
                v-for="size in (product.size_options || [])"
                :key="size"
                type="button"
                @click="selectedSize = size"
                :class="size === selectedSize ? 'bg-black text-white' : 'bg-gray-100 text-slate-700'"
                class="rounded-full px-4 py-2 text-sm font-semibold transition"
              >
                {{ size }}
              </button>
            </div>
            <p v-if="!product.size_options || product.size_options.length === 0" class="text-sm text-gray-500 mt-3">No size options available for this item.</p>
          </div>
        </div>
      </div>

      <div class="product-meta-details space-y-6">
        <div class="rounded-[2rem] border border-gray-100 bg-white p-8 shadow-lg shadow-slate-200/50">
          <div class="mb-6">
            <h1 class="text-5xl font-extrabold tracking-tight mb-3">{{ product.name }}</h1>
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
              class="w-full rounded-full py-4 text-lg font-bold transition shadow-lg text-white bg-black hover:bg-slate-900 disabled:cursor-not-allowed disabled:bg-gray-300"
            >
              {{ product.in_stock ? 'Add to Cart' : 'Out of Stock' }}
            </button>
            <p v-if="product.size_options && product.size_options.length > 0 && !selectedSize" class="text-sm text-red-500">Please choose a size before adding to cart.</p>
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
  </div>

  <!-- Lightbox Modal Layout -->
  <div v-if="isLightboxOpen" 
       class="fixed inset-0 z-50 bg-black/95 flex flex-col items-center justify-center p-4 backdrop-blur-md select-none"
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

      <div class="flex-1 flex justify-center items-center max-h-[75vh]">
        <video v-if="currentLightboxMedia?.media_type === 'video'" 
               :src="currentLightboxMedia.url" 
               controls 
               autoplay
               class="max-w-full max-h-[75vh] object-contain rounded-xl shadow-2xl"></video>
        
        <img v-else 
             :src="currentLightboxMedia?.url" 
             :alt="product?.name" 
             class="max-w-full max-h-[75vh] object-contain rounded-xl shadow-2xl" />
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

// 1. Core States defined first
const product = ref(null)
const selectedSize = ref('')
const showSuccessMessage = ref(false)

const activeMediaIndex = ref(0)
const isLightboxOpen = ref(false)
const lightboxIndex = ref(0)

const route = useRoute()
const cartStore = useCartStore()

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

  cartStore.addToCart({
    ...product.value,
    price: parsedPrice
  }, selectedSize.value, 1)

  showSuccessMessage.value = true
  setTimeout(() => {
    showSuccessMessage.value = false
  }, 2000)
}
</script>