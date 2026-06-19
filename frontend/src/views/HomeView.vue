<template>
  <div class="home-page font-brand text-brand-text">
    
    <div class="hero-section relative h-[450px] overflow-hidden bg-black flex items-center justify-center text-center px-4" style="perspective: 1800px;">
      
      <div 
        v-for="(image, index) in config.heroImages" 
        :key="index"
        class="absolute inset-0 bg-cover bg-center transition-opacity duration-1000 ease-in-out transform-gpu"
        :class="index === currentSlide ? 'opacity-100 z-10' : 'opacity-0 z-0'"
        :style="{ backgroundImage: `linear-gradient(rgba(0,0,0,0.4), rgba(0,0,0,0.4)), url(${image})`, transform: index === currentSlide ? 'translateZ(0)' : 'translateZ(-10px)' }"
      ></div>

      <div class="max-w-2xl text-white relative z-20">
        <h1 class="text-4xl md:text-5xl font-extrabold mb-4 tracking-tight drop-shadow-md">
          {{ config.heroBannerTitle }}
        </h1>
        <p class="text-lg md:text-xl mb-6 opacity-90 drop-shadow-sm">
          {{ config.heroBannerSubtitle }}
        </p>
        <a 
          href="#latest-products" 
          class="inline-block bg-white text-black font-bold px-6 py-3 rounded shadow hover:bg-gray-100 transition duration-200 transformation active:scale-95"
        >
          Shop Latest Drop
        </a>

        <div class="flex justify-center gap-2 mt-8">
          <button 
            v-for="(item, index) in config.heroImages" 
            :key="index"
            @click="currentSlide = index"
            class="w-2.5 h-2.5 rounded-full transition-all duration-300"
            :class="index === currentSlide ? 'bg-white scale-125' : 'bg-white/40'"
          ></button>
        </div>
      </div>
    </div>

    <div id="latest-products" class="max-w-7xl mx-auto px-6 py-16">
      <div class="flex flex-col md:flex-row justify-between items-start md:items-end mb-10">
        <div>
          <h2 class="text-3xl font-bold tracking-tight mb-2">{{ categoryTitle }}</h2>
          <p class="text-gray-500">Freshly added pieces from our design room.</p>
        </div>
        
        <router-link 
          v-if="config.enableTrackingPage" 
          to="/order-history" 
          class="mt-4 md:mt-0 text-sm font-semibold underline hover:text-gray-600"
        >
          Track An Existing Order →
        </router-link>
      </div>

      <div v-if="isLoading" class="text-center py-12 text-gray-400 font-medium">
        Loading fresh catalog...
      </div>

      <div v-else class="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-8">
        <div 
          v-for="product in products" 
          :key="product.id" 
          class="product-card group flex flex-col justify-between"
        >
          <router-link :to="`/products/${product.slug}`" class="block overflow-hidden rounded-3xl bg-brand-muted aspect-square mb-4 transform-gpu transition duration-500 hover:-translate-y-1 hover:scale-[1.02] hover:shadow-2xl hover:shadow-blue-500/20">
            <img 
              :src="product.get_thumbnail || 'https://placehold.co/400'" 
              :alt="product.name"
              class="w-full h-full object-cover object-center group-hover:scale-105 transition duration-300"
              @error="(e) => e.target.src = 'https://placehold.co/400'"
            />
          </router-link>

          <div>
            <h3 class="font-bold text-base mb-1 group-hover:underline">
              <router-link :to="`/products/${product.slug}`">{{ product.name }}</router-link>
            </h3>
            <p class="text-brand-accent font-bold text-sm">
              {{ product.price }} {{ config.currencySymbol }}
            </p>
          </div>
        </div>
      </div>
    </div>

  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount, watch } from 'vue'
import { useRoute } from 'vue-router'
import axios from 'axios'
import { BRAND_CONFIG } from '../brand.config.js'

const config = ref(BRAND_CONFIG)
const products = ref([])
const isLoading = ref(true)
const route = useRoute()
const categorySlug = ref(route.params.category_slug || '')
const categoryTitle = ref(categorySlug.value ? `Category: ${categorySlug.value.replace(/-/g, ' ')}` : 'New Arrivals')

// 🌟 Slide Tracker States
const currentSlide = ref(0)
let sliderInterval = null

const startImageRotation = () => {
  sliderInterval = setInterval(() => {
    if (config.value.heroImages && config.value.heroImages.length > 0) {
      currentSlide.value = (currentSlide.value + 1) % config.value.heroImages.length
    }
  }, 3000) // ⏱️ Rotates images automatically every 5 seconds
}

const fetchLatestProducts = async () => {
  isLoading.value = true
  try {
    const endpoint = categorySlug.value ? `/api/v1/products/category/${categorySlug.value}/` : '/api/v1/latest-products/'
    const response = await axios.get(endpoint)

    if (Array.isArray(response.data)) {
      products.value = response.data
    } else if (response.data && Array.isArray(response.data.products)) {
      products.value = response.data.products
    } else {
      products.value = response.data.results || []
    }

    categoryTitle.value = categorySlug.value
      ? `Category: ${categorySlug.value.replace(/-/g, ' ')}`
      : 'New Arrivals'
  } catch (error) {
    console.error('Error loading frontend shelf:', error)
    products.value = []
  } finally {
    isLoading.value = false
  }
}

onMounted(() => {
  fetchLatestProducts()
  startImageRotation() // 🌟 Spin up the image timer loop
})

watch(route, () => {
  categorySlug.value = route.params.category_slug || ''
  fetchLatestProducts()
})

onBeforeUnmount(() => {
  if (sliderInterval) clearInterval(sliderInterval) // 🧹 Clean up timer memory
})
</script>