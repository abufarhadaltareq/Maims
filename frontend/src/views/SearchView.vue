<template>
  <div class="p-8 max-w-7xl mx-auto">
    <h2 class="text-xl font-bold mb-6">
      Search Results for: <span class="text-brand">"{{ route.query.q }}"</span>
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
import { useRoute } from 'vue-router'
import axios from 'axios'
import { useCartStore } from '../stores/cart'
import { formatProductPrice } from '../utils/pricing.js'
import ProductCard from '../components/ProductCard.vue'

const route = useRoute()
const cartStore = useCartStore()
const products = ref([])
const loading = ref(false)

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

watch(() => route.query.q, fetchResults, { immediate: true })
</script>