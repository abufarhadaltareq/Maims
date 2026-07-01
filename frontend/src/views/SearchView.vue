<template>
  <div class="p-8">
    <h2 class="text-xl font-bold mb-6">
      Search Results for: <span class="text-blue-600">"{{ route.query.q }}"</span>
    </h2>

    <div v-if="loading" class="text-gray-500">Searching...</div>

    <div v-else-if="products.length > 0" class="grid grid-cols-2 md:grid-cols-4 gap-6">
      <div v-for="product in products" :key="product.id" class="border p-4 rounded-lg">
        <img :src="product.image" class="w-full h-48 object-cover mb-2">
        <h3 class="font-bold">{{ product.name }}</h3>
        <p>{{ product.price }}</p>
      </div>
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

const route = useRoute()
const products = ref([])
const loading = ref(false)

const fetchResults = async () => {
  const query = route.query.q
  if (!query) return

  loading.value = true
  try {
    // IMPORTANT: Verify this URL matches your actual backend API endpoint
    const res = await axios.get(`/api/v1/products/search/?q=${query}`)
    products.value = res.data
    console.log("API Response:", res.data) // Check console to see if data arrives
  } catch (e) {
    console.error("Search failed:", e)
  } finally {
    loading.value = false
  }
}

watch(() => route.query.q, fetchResults, { immediate: true })
</script>