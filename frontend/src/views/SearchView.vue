<template>
  <div class="mx-auto max-w-7xl px-4 py-8 sm:px-6">
    <form @submit.prevent="submitSearch" class="mb-7 flex border-b border-black pb-3">
      <label for="product-search" class="sr-only">Search products</label>
      <input
        id="product-search"
        v-model="searchQuery"
        type="search"
        placeholder="Search products"
        class="min-w-0 flex-1 bg-transparent text-lg outline-none placeholder:text-gray-400"
      />
      <button type="submit" class="border border-black bg-black px-5 py-2 text-sm font-medium text-white hover:bg-white hover:text-black">Search</button>
    </form>

    <h2 v-if="route.query.q" class="mb-5 text-sm font-medium text-gray-600">
      Results for “{{ route.query.q }}”
    </h2>

    <div v-if="loading" class="text-gray-500">Searching...</div>

    <div v-else-if="products.length > 0" class="grid grid-cols-2 md:grid-cols-4 gap-6">
      <ProductCard
        v-for="product in products"
        :key="product.id"
        :product="product"
      />
    </div>

    <div v-else class="text-gray-500">
      No products found for this search.
    </div>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import axios from 'axios'
import { useCartStore } from '../stores/cart'
import { formatProductPrice } from '../utils/pricing.js'
import ProductCard from '../components/ProductCard.vue'

const route = useRoute()
const router = useRouter()
const cartStore = useCartStore()
const products = ref([])
const loading = ref(false)
const searchQuery = ref(String(route.query.q || ''))

const priceFor = (p) => formatProductPrice(p, cartStore.currentCurrency)

const fetchResults = async () => {
  const query = (route.query.q || '').trim()
  if (!query) {
    products.value = []
    return
  }

  loading.value = true
  try {
    const res = await axios.get(`/api/v1/products/search/?q=${encodeURIComponent(query)}`)
    const data = res.data
    products.value = Array.isArray(data) ? data : (data.results || data.products || [])
  } catch (e) {
    console.error("Search failed:", e)
    products.value = []
  } finally {
    loading.value = false
  }
}

const submitSearch = () => {
  const query = searchQuery.value.trim()
  router.push({ path: '/search', query: query ? { q: query } : {} })
}

watch(() => route.query.q, (query) => {
  searchQuery.value = String(query || '')
  fetchResults()
}, { immediate: true })
</script>