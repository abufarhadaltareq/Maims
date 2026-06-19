<template>
  <div class="py-10 px-8 max-w-7xl mx-auto font-brand text-brand-text">
    <router-link to="/" class="inline-block mb-8 text-sm font-semibold underline hover:text-gray-600">
      ← Back to New Arrivals
    </router-link>

    <div v-if="product" class="grid grid-cols-1 lg:grid-cols-[1.4fr_1fr] gap-12 items-start">
      <div class="space-y-8">
        <div class="relative rounded-[2rem] overflow-hidden shadow-2xl shadow-slate-300/40 transform-gpu hover:-translate-y-1 transition-all duration-500 bg-white">
          <div class="h-[520px] bg-slate-900/5 flex items-center justify-center overflow-hidden">
            <template v-if="activeMedia">
              <video v-if="activeMedia.media_type === 'video'" :src="activeMedia.url" controls class="w-full h-full object-cover"></video>
              <img v-else :src="activeMedia.url || product.get_image || 'https://placehold.co/600x800'" :alt="product.name" class="w-full h-full object-cover" />
            </template>
          </div>
          <div class="absolute bottom-4 left-4 right-4 flex gap-3 overflow-x-auto no-scrollbar">
            <button
              v-for="(media, index) in product.media"
              :key="media.id"
              @click="setActiveMedia(index)"
              type="button"
              class="min-w-[96px] h-24 rounded-3xl border border-white/80 bg-white/90 shadow-lg overflow-hidden transition-transform duration-300 hover:-translate-y-1"
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
                v-for="size in product.size_options"
                :key="size"
                type="button"
                @click="selectedSize = size"
                :class="size === selectedSize ? 'bg-black text-white' : 'bg-gray-100 text-slate-700'"
                class="rounded-full px-4 py-2 text-sm font-semibold transition"
              >
                {{ size }}
              </button>
            </div>
            <p v-if="product.size_options.length === 0" class="text-sm text-gray-500 mt-3">No size options available for this item.</p>
          </div>
        </div>
      </div>

      <div class="product-meta-details space-y-6">
        <div class="rounded-[2rem] border border-gray-100 bg-white p-8 shadow-lg shadow-slate-200/50">
          <div class="mb-6">
            <h1 class="text-5xl font-extrabold tracking-tight mb-3">{{ product.name }}</h1>
            <div class="flex items-center gap-3">
              <span class="text-4xl font-black text-brand-accent">{{ product.price }} €</span>
              <span class="inline-flex rounded-full border border-slate-200 px-3 py-1 text-xs font-semibold uppercase tracking-[0.25em] text-slate-500">{{ product.in_stock ? 'Ready to ship' : 'Sold out' }}</span>
            </div>
          </div>

          <div class="space-y-4 mb-6">
            <p class="text-slate-600 leading-relaxed">{{ product.description || 'A refined product list with premium fabric, tailored fit, and layered visuals that feel luxurious.' }}</p>
            <div class="grid grid-cols-2 gap-3 text-sm text-slate-500">
              <div class="rounded-3xl bg-slate-50 p-4">
                <span class="block uppercase tracking-[0.22em] font-semibold">Category</span>
                <span class="block mt-2 text-slate-800">{{ product.category.name }}</span>
              </div>
              <div class="rounded-3xl bg-slate-50 p-4">
                <span class="block uppercase tracking-[0.22em] font-semibold">Added</span>
                <span class="block mt-2 text-slate-800">{{ new Date(product.date_added).toLocaleDateString() }}</span>
              </div>
            </div>
          </div>

          <div class="space-y-4">
            <button
              @click="addToCart"
              :disabled="!product.in_stock || (product.size_options.length > 0 && !selectedSize)"
              class="w-full rounded-full py-4 text-lg font-bold transition shadow-lg text-white bg-black hover:bg-slate-900 disabled:cursor-not-allowed disabled:bg-gray-300"
            >
              {{ product.in_stock ? 'Add to Cart' : 'Out of Stock' }}
            </button>
            <p v-if="product.size_options.length > 0 && !selectedSize" class="text-sm text-red-500">Please choose a size before adding to cart.</p>
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
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRoute } from 'vue-router'
import axios from 'axios'

// 1. Import the cart store
import { useCartStore } from '../stores/cart'

const product = ref(null)
const route = useRoute()
const cartStore = useCartStore()
const showSuccessMessage = ref(false)
const selectedSize = ref('')
const activeMediaIndex = ref(0)

onMounted(async () => {
  const slug = route.params.slug
  try {
    const response = await axios.get(`/api/v1/products/${slug}/`)
    product.value = response.data
    if (product.value?.media?.length > 0) {
      activeMediaIndex.value = 0
    }
  } catch (error) {
    console.error('Error fetching product details payload:', error)
  }
})

const activeMedia = computed(() => {
  if (!product.value?.media?.length) return null
  return product.value.media[activeMediaIndex.value]
})

const hasSizeSelection = computed(() => {
  return Array.isArray(product.value?.size_options) && product.value.size_options.length > 0
})

function setActiveMedia(index) {
  activeMediaIndex.value = index
}

function addToCart() {
  if (!product.value) return

  if (hasSizeSelection.value && !selectedSize.value) {
    return
  }

  cartStore.addToCart(product.value, selectedSize.value, 1)
  showSuccessMessage.value = true
  setTimeout(() => {
    showSuccessMessage.value = false
  }, 2000)
}
</script>