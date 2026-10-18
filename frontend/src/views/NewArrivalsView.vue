<template>
  <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 font-brand text-brand-text">
    <!-- Header -->
    <div class="flex flex-col sm:flex-row sm:items-end justify-between gap-4 mb-6">
      <div>
        <p class="text-[11px] uppercase tracking-[0.3em] text-brand-accent font-bold mb-1.5">Catalog</p>
        <h1 class="text-2xl sm:text-3xl font-extrabold tracking-tight">New Arrivals</h1>
        <p class="text-gray-500 text-sm mt-1">{{ totalCount }} fresh pieces{{ socialCount ? ` · ${socialCount} synced from Facebook` : '' }}</p>
      </div>
      <!-- Sort -->
      <div class="flex items-center gap-2">
        <label for="sort" class="text-xs font-bold uppercase tracking-wider text-gray-400">Sort</label>
        <select id="sort" v-model="sortKey" class="text-sm font-semibold border border-gray-200 rounded-full px-4 py-2 bg-white outline-none focus:border-brand-accent cursor-pointer">
          <option value="newest">Newest first</option>
          <option value="price-asc">Price: low → high</option>
          <option value="price-desc">Price: high → low</option>
          <option value="rating">Top rated</option>
          <option value="name">Name A–Z</option>
        </select>
        <button
          @click="showSocialOnly = !showSocialOnly"
          :class="showSocialOnly ? 'bg-[#1877F2] text-white border-[#1877F2]' : 'bg-white text-gray-600 border-gray-200'"
          class="text-xs font-bold border rounded-full px-4 py-2 transition hover:shadow flex items-center gap-1.5 whitespace-nowrap"
        >
          <span class="w-1.5 h-1.5 rounded-full" :class="showSocialOnly ? 'bg-white animate-pulse' : 'bg-[#1877F2]'"></span>
          Facebook live
        </button>
      </div>
    </div>

    <div v-if="loading" class="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4 sm:gap-5">
      <div v-for="i in 12" :key="'sk-'+i" class="rounded-2xl overflow-hidden border border-gray-100 bg-white">
        <div class="aspect-[3/4] bg-gray-100 animate-pulse"></div>
        <div class="p-3.5 space-y-2">
          <div class="h-3.5 bg-gray-100 rounded animate-pulse w-3/4"></div>
          <div class="h-3.5 bg-gray-100 rounded animate-pulse w-1/2"></div>
        </div>
      </div>
    </div>

    <div v-else-if="!sorted.length" class="text-center py-16 border border-dashed border-gray-200 rounded-2xl bg-gray-50/60">
      <p class="font-bold text-lg text-gray-700">{{ showSocialOnly ? 'No Facebook drops yet' : 'No arrivals yet' }}</p>
      <p class="text-gray-400 text-sm mt-1 mb-5">{{ showSocialOnly ? 'Sync the Page to fill this shelf.' : 'Fresh pieces are on the way.' }}</p>
      <button v-if="showSocialOnly" @click="showSocialOnly = false" class="text-sm font-bold bg-[var(--color-brand)] text-white px-5 py-2.5 rounded-full hover:bg-[var(--color-brand)]/80 transition">Show everything</button>
      <router-link v-else to="/" class="inline-block text-sm font-bold bg-[var(--color-brand)] text-white px-5 py-2.5 rounded-full hover:bg-[var(--color-brand)]/80 transition">Back to homepage</router-link>
    </div>

    <div v-else class="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4 sm:gap-5">
      <ProductCard v-for="product in sorted" :key="product.id" :product="product" />
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import axios from 'axios'
import ProductCard from '../components/ProductCard.vue'
import { getProductDisplayPrice } from '../utils/pricing.js'
import { useCartStore } from '../stores/cart'

const cartStore = useCartStore()
const products = ref([])
const loading = ref(true)
const sortKey = ref('newest')
const showSocialOnly = ref(false)

const priceOf = (p) => getProductDisplayPrice(p || {}, cartStore.currentCurrency).numeric || 0
const isSocial = (p) => !!(p?.facebook_post_id || p?.facebook_image_url)

const socialCount = computed(() => products.value.filter(isSocial).length)

const visible = computed(() => showSocialOnly.value ? products.value.filter(isSocial) : products.value)

const sorted = computed(() => {
  const list = [...visible.value]
  switch (sortKey.value) {
    case 'price-asc': return list.sort((a, b) => priceOf(a) - priceOf(b))
    case 'price-desc': return list.sort((a, b) => priceOf(b) - priceOf(a))
    case 'rating': return list.sort((a, b) => (Number(b.average_rating) || 0) - (Number(a.average_rating) || 0))
    case 'name': return list.sort((a, b) => String(a.name || '').localeCompare(String(b.name || '')))
    default: return list.sort((a, b) => new Date(b.date_added || 0) - new Date(a.date_added || 0))
  }
})

const totalCount = computed(() => visible.value.length)

onMounted(async () => {
  loading.value = true
  try {
    // One call returns newest-first for the whole catalog; social filter is client-side.
    const res = await axios.get('/api/v1/products/')
    const data = res.data
    products.value = Array.isArray(data) ? data : (data.results || data.products || [])
  } catch (e) {
    console.error('New arrivals failed:', e)
    products.value = []
  } finally {
    loading.value = false
  }
})
</script>
