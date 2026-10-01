<template>
  <div class="home-page font-brand text-brand-text">

    <!-- Dynamic hero: admin HeroSlides, fallback to brand.config images -->
    <div v-if="isHomePage && heroSlides.length" class="hero-section relative h-[500px] overflow-hidden bg-black flex items-center justify-center text-center px-4" style="perspective: 1800px;">
      
      <!-- Animated 3D Background component -->
      <Hero3D />

      <div
        v-for="(slide, index) in heroSlides"
        :key="slide.id || index"
        class="absolute inset-0 bg-cover bg-center transition-opacity duration-1000 ease-in-out transform-gpu"
        :class="index === currentSlide ? 'opacity-100 z-10' : 'opacity-0 z-0'"
        :style="{ backgroundImage: `linear-gradient(rgba(0,0,0,0.4), rgba(0,0,0,0.4)), url(${slide.image_url})`, transform: index === currentSlide ? 'translateZ(0)' : 'translateZ(-10px)' }"
      ></div>

      <div class="max-w-2xl text-white relative z-20 backdrop-blur-sm bg-black/20 p-8 rounded-2xl border border-white/10">
        <h1 class="text-5xl md:text-6xl font-extrabold mb-4 tracking-tight drop-shadow-lg text-transparent bg-clip-text bg-gradient-to-r from-white to-gray-400">
          {{ heroSlides[currentSlide]?.title }}
        </h1>
        <p v-if="heroSlides[currentSlide]?.subtitle" class="text-xl md:text-2xl mb-8 opacity-90 drop-shadow-sm font-light">
          {{ heroSlides[currentSlide]?.subtitle }}
        </p>
        <component
          :is="isInternalLink(heroSlides[currentSlide]?.button_link) ? 'router-link' : 'a'"
          v-if="heroSlides[currentSlide]?.button_text"
          :to="isInternalLink(heroSlides[currentSlide]?.button_link) ? heroSlides[currentSlide].button_link : undefined"
          :href="!isInternalLink(heroSlides[currentSlide]?.button_link) ? heroSlides[currentSlide].button_link : undefined"
          class="inline-block bg-white text-black font-bold px-8 py-4 rounded-full shadow-[0_0_15px_rgba(255,255,255,0.3)] hover:shadow-[0_0_25px_rgba(255,255,255,0.5)] hover:scale-105 transition-all duration-300 active:scale-95 uppercase tracking-widest text-sm"
        >
          {{ heroSlides[currentSlide]?.button_text }}
        </component>

        <div v-if="heroSlides.length > 1" class="flex justify-center gap-3 mt-10">
          <button
            v-for="(item, index) in heroSlides"
            :key="item.id || index"
            @click="goToSlide(index)"
            class="w-2.5 h-2.5 rounded-full transition-all duration-300"
            :class="index === currentSlide ? 'bg-white scale-125' : 'bg-white/40'"
          ></button>
        </div>
      </div>
    </div>

    <!-- Shop by Category strip (only on homepage, driven by admin flags) -->
    <div v-if="isHomePage && showcase.length" class="max-w-7xl mx-auto px-6 pt-14">
      <div class="flex items-end justify-between mb-6">
        <div>
          <h2 class="text-3xl font-bold tracking-tight mb-1">Shop by Category</h2>
          <p class="text-gray-500">Curated collections — pick a lane, find your fit.</p>
        </div>
      </div>
      <div class="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-5">
        <router-link
          v-for="entry in showcase"
          :key="entry.category.id"
          :to="`/category/${entry.category.slug}`"
          class="group relative overflow-hidden rounded-3xl bg-brand-muted aspect-[4/5]"
        >
          <img
            :src="entry.category.image_url || entry.products[0]?.get_thumbnail || entry.products[0]?.get_image || 'https://placehold.co/600x750'"
            :alt="entry.category.name"
            class="w-full h-full object-cover group-hover:scale-105 transition duration-500"
            loading="lazy"
          />
          <div class="absolute inset-0 bg-gradient-to-t from-black/70 via-black/10 to-transparent"></div>
          <div class="absolute bottom-0 left-0 right-0 p-5 text-left text-white">
            <p class="text-[11px] uppercase tracking-[0.25em] opacity-80 font-bold">{{ entry.category.product_count }} items</p>
            <h3 class="text-xl font-extrabold leading-tight">{{ entry.category.name }}</h3>
            <span class="inline-block mt-2 text-xs font-bold bg-white text-black px-3 py-1.5 rounded-full group-hover:bg-black group-hover:text-white transition">Shop now →</span>
          </div>
        </router-link>
      </div>
    </div>

    <!-- Category-wise shopping sections (homepage only) -->
    <div v-if="isHomePage && showcase.length" class="max-w-7xl mx-auto px-6 pt-14 space-y-16">
      <section v-for="entry in showcase" :key="'sec-' + entry.category.id">
        <div class="flex items-end justify-between mb-6">
          <div>
            <h2 class="text-2xl font-bold tracking-tight mb-1">{{ entry.category.name }}</h2>
            <p v-if="entry.category.description" class="text-gray-500 text-sm max-w-xl">{{ entry.category.description }}</p>
          </div>
          <router-link :to="`/category/${entry.category.slug}`" class="text-sm font-semibold underline hover:text-gray-600 whitespace-nowrap ml-4">
            View all →
          </router-link>
        </div>
        <div v-if="entry.products.length === 0" class="text-gray-400 text-sm py-6">No items in this category yet.</div>
        <div v-else class="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-6">
          <div v-for="product in entry.products" :key="product.id" class="product-card group flex flex-col justify-between">
            <router-link :to="`/products/${product.slug}`" class="block overflow-hidden rounded-3xl bg-brand-muted aspect-square mb-3">
              <img :src="product.get_thumbnail || 'https://placehold.co/400'" class="w-full h-full object-cover group-hover:scale-105 transition duration-300" :alt="product.name" loading="lazy" />
            </router-link>
            <div>
              <p v-if="product.brand_name" class="text-xs uppercase tracking-widest text-gray-400 font-bold mb-0.5">{{ product.brand_name }}</p>
              <h3 class="font-bold text-base mb-1 group-hover:underline leading-tight">{{ product.name }}</h3>
              <p class="text-brand-accent font-bold text-sm">{{ formatPrice(product) }}</p>
            </div>
          </div>
        </div>
      </section>
    </div>

    <div id="latest-products" class="max-w-7xl mx-auto px-6 py-16">
      <div class="flex flex-col md:flex-row justify-between items-start md:items-end mb-10">
        <div>
          <h2 class="text-3xl font-bold tracking-tight mb-2">{{ categoryTitle }}</h2>
          <p class="text-gray-500">Freshly added pieces from our design room.</p>
import Hero3D from '../components/Hero3D.vue'
        </div>
        <router-link 
          v-if="config.enableTrackingPage" 
          to="/order-history" 
          class="mt-4 md:mt-0 text-sm font-semibold underline hover:text-gray-600"
        >
          Track An Existing Order →
        </router-link>
      </div>

      <div v-if="isLoading" class="text-center py-12 text-gray-400 font-medium">Loading fresh catalog...</div>
      <div v-else-if="products.length === 0" class="text-center py-12 text-gray-500">No items found in this section yet.</div>
      <div v-else class="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-8">
        <div v-for="product in products" :key="product.id" class="product-card group flex flex-col justify-between">
           <router-link :to="`/products/${product.slug}`" class="block overflow-hidden rounded-3xl bg-brand-muted aspect-square mb-4">
            <img :src="product.get_thumbnail || 'https://placehold.co/400'" class="w-full h-full object-cover group-hover:scale-105 transition duration-300" />
          </router-link>
          <div>
            <p v-if="product.brand_name" class="text-xs uppercase tracking-widest text-gray-400 font-bold mb-0.5">{{ product.brand_name }}</p>
            <h3 class="font-bold text-base mb-1 group-hover:underline">{{ product.name }}</h3>
            <p class="text-brand-accent font-bold text-sm">{{ formatPrice(product) }}</p>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount, watch } from 'vue' // Added computed
import { useRoute } from 'vue-router'
import axios from 'axios'
import { BRAND_CONFIG } from '../brand.config.js'
import { useCartStore } from '../stores/cart'
import { formatProductPrice } from '../utils/pricing.js'

const route = useRoute()
const cartStore = useCartStore()
const config = ref(BRAND_CONFIG)
const products = ref([])
const isLoading = ref(true)
const categorySlug = ref(route.params.category_slug || '')
const categoryTitle = ref('New Arrivals')
const heroSlides = ref([])
const showcase = ref([])

// 🌟 FIX: Computed property to detect Home Page
const isHomePage = computed(() => route.path === '/')

const currentSlide = ref(0)
let sliderInterval = null

const isInternalLink = (link) => {
  if (!link) return false
  return link.startsWith('/') || link.startsWith('#')
}

// ... (keep your existing functions: startImageRotation, formatPrice, fetchLatestProducts)

const fallbackSlides = () => {
  const imgs = config.value.heroImages || []
  return imgs.map((image_url, i) => ({
    id: `fallback-${i}`,
    title: i === 0 ? config.value.heroBannerTitle : config.value.heroBannerTitle,
    subtitle: i === 0 ? config.value.heroBannerSubtitle : '',
    button_text: 'Shop Latest Drop',
    button_link: '#latest-products',
    image_url,
  }))
}

const fetchHeroSlides = async () => {
  try {
    const res = await axios.get('/api/v1/hero-slides/')
    const slides = Array.isArray(res.data) ? res.data.filter((s) => s.image_url) : []
    heroSlides.value = slides.length ? slides : fallbackSlides()
  } catch (e) {
    console.warn('Hero slides fallback to brand config:', e?.message)
    heroSlides.value = fallbackSlides()
  } finally {
    if (currentSlide.value >= heroSlides.value.length) currentSlide.value = 0
  }
}

const fetchShowcase = async () => {
  if (!isHomePage.value) return
  try {
    const res = await axios.get('/api/v1/category-showcase/')
    showcase.value = Array.isArray(res.data) ? res.data : []
  } catch (e) {
    console.error('Error loading category showcase:', e)
    showcase.value = []
  }
}

const startImageRotation = () => {
  if (sliderInterval) clearInterval(sliderInterval)
  sliderInterval = setInterval(() => {
    if (heroSlides.value && heroSlides.value.length > 1) {
      currentSlide.value = (currentSlide.value + 1) % heroSlides.value.length
    }
  }, 4000)
}

const goToSlide = (index) => {
  currentSlide.value = index
  startImageRotation() // reset timer on manual click
}

const formatPrice = (product) => {
  // Unified pricing helper: exact currency -> conversion fallback -> product.price fallback.
  return formatProductPrice(product, cartStore.currentCurrency)
}

const fetchLatestProducts = async () => {
  isLoading.value = true
  try {
    let endpoint = '/api/v1/products/'
    if (categorySlug.value) endpoint += `?category=${categorySlug.value}`
    const response = await axios.get(endpoint)
    products.value = response.data.results || response.data.products || (Array.isArray(response.data) ? response.data : [])
    categoryTitle.value = categorySlug.value ? `Category: ${categorySlug.value.replace(/-/g, ' ')}` : 'New Arrivals'
  } catch (error) {
    console.error('Error loading products:', error)
    products.value = []
  } finally {
    isLoading.value = false
  }
}

onMounted(async () => {
  await fetchHeroSlides()
  fetchLatestProducts()
  fetchShowcase()
  startImageRotation()
})

watch(() => route.params.category_slug, (newSlug) => {
  categorySlug.value = newSlug || ''
  fetchLatestProducts()
})

watch(() => route.path, (p) => {
  if (p === '/') fetchShowcase()
})

onBeforeUnmount(() => {
  if (sliderInterval) clearInterval(sliderInterval)
})
</script>