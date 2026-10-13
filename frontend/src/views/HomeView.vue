<template>
  <div class="home-page font-brand text-brand-text">

    <!-- ===== Hero — fills the viewport, animated slides ===== -->
    <div
      v-if="isHomePage && heroSlides.length"
      class="hero-section relative w-full min-h-[52svh] sm:min-h-[56svh] md:min-h-[64svh] lg:min-h-[72svh] overflow-hidden bg-slate-950 flex items-center justify-center text-center"
      style="perspective: 1800px;"
    >
      <!-- Animated 3D Background component -->
      <Hero3D />

      <div
        v-for="(slide, index) in heroSlides"
        :key="slide.id || index"
        class="absolute inset-0 bg-cover bg-center transition-opacity duration-1000 ease-in-out"
        :class="index === currentSlide ? 'opacity-100 z-10 animate-kenburns' : 'opacity-0 z-0'"
        :style="{ backgroundImage: `linear-gradient(rgba(0,0,0,0.45), rgba(0,0,0,0.30)), url(${slide.image_url})`, transform: index === currentSlide ? 'translateZ(0)' : 'translateZ(-10px)' }"
      ></div>

      <!-- Animated readability gradient -->
      <div class="absolute inset-0 z-[5] pointer-events-none animate-hero-glow bg-gradient-to-b from-black/50 via-black/10 to-black/65"></div>

      <!-- Copy — re-keyed per slide so the entrance animation replays -->
      <div :key="currentSlide" class="max-w-3xl w-full text-white relative z-20 px-4 py-10">
        <p class="animate-fade-up inline-flex items-center gap-2 text-[11px] font-extrabold uppercase tracking-[0.28em] bg-white/12 backdrop-blur-md border border-white/20 rounded-full px-4 py-1.5 mb-5" style="animation-delay: 0s">
          <span class="w-1.5 h-1.5 rounded-full bg-emerald-300 animate-pulse"></span>
          New season drop
        </p>
        <h1 class="animate-fade-up text-4xl sm:text-5xl md:text-6xl font-extrabold mb-4 tracking-tight drop-shadow-lg text-balance" style="animation-delay: .05s">
          {{ heroSlides[currentSlide]?.title }}
        </h1>
        <p v-if="heroSlides[currentSlide]?.subtitle" class="animate-fade-up text-base sm:text-lg md:text-xl mb-7 opacity-90 drop-shadow-sm font-light max-w-2xl mx-auto text-balance" style="animation-delay: .2s">
          {{ heroSlides[currentSlide]?.subtitle }}
        </p>
        <div class="animate-fade-up flex flex-wrap items-center justify-center gap-3" style="animation-delay: .35s">
        <component
          :is="isInternalLink(heroSlides[currentSlide]?.button_link) ? 'router-link' : 'a'"
          v-if="heroSlides[currentSlide]?.button_text"
          :to="isInternalLink(heroSlides[currentSlide]?.button_link) ? heroSlides[currentSlide].button_link : undefined"
          :href="!isInternalLink(heroSlides[currentSlide]?.button_link) ? heroSlides[currentSlide].button_link : undefined"
          class="inline-block bg-white text-slate-900 font-extrabold px-7 py-3.5 rounded-full shadow-lg hover:shadow-xl hover:scale-105 transition-all duration-300 active:scale-95 uppercase tracking-widest text-[13px]"
        >
          {{ heroSlides[currentSlide]?.button_text }}
        </component>
        <router-link
          to="/new-arrivals"
          class="inline-block font-extrabold px-7 py-3.5 rounded-full uppercase tracking-widest text-[13px] border border-white/40 text-white backdrop-blur-md bg-white/10 hover:bg-white/20 transition-all duration-300 active:scale-95"
        >
          New arrivals
        </router-link>
        </div>

        <!-- Progress indicators (one bar fills per rotation) -->
        <div v-if="heroSlides.length > 1" class="animate-fade-up flex justify-center gap-2 mt-10" style="animation-delay: .5s">
          <button
            v-for="(item, index) in heroSlides"
            :key="item.id || index"
            @click="goToSlide(index)"
            class="h-1 rounded-full transition-all duration-300 overflow-hidden"
            :class="index === currentSlide ? 'w-10 bg-white/25' : 'w-4 bg-white/30 hover:bg-white/60'"
            :aria-label="`Go to slide ${index + 1}`"
          >
            <span
              v-if="index === currentSlide"
              :key="`fill-${currentSlide}`"
              class="block h-full bg-gradient-brand animate-hero-progress"
            ></span>
          </button>
        </div>
      </div>

      <!-- Scroll cue -->
      <div class="absolute bottom-5 left-1/2 -translate-x-1/2 z-20 animate-bounce text-white/70 hover:text-white transition-colors">
        <svg class="w-6 h-6" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" d="M19 14l-7 7-7-7M19 5l-7 7-7-7"></path>
        </svg>
      </div>
    </div>

    <!-- ===== Shop by Category — round balls, directly under the hero ===== -->
    <section v-if="isHomePage && showcase.length" v-reveal class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-10 pb-4">
      <div class="text-center mb-8">
        <p class="text-[11px] uppercase tracking-[0.3em] text-brand-accent font-bold mb-2">Collections</p>
        <h2 class="text-3xl font-bold tracking-tight text-gradient-brand">Shop by Category</h2>
        <p class="text-gray-500 mt-2">Curated collections — pick a lane, find your fit.</p>
      </div>
      <div class="grid grid-cols-3 sm:grid-cols-4 lg:grid-cols-6 gap-x-3 gap-y-8">
        <router-link
          v-for="(entry, i) in showcase"
          :key="'ball-' + entry.category.id"
          :to="`/category/${entry.category.slug}`"
          v-reveal="i * 70"
          class="group flex flex-col items-center gap-3"
        >
          <div class="relative w-full max-w-[110px] sm:max-w-[140px] lg:max-w-[160px] aspect-square rounded-full overflow-hidden ring-1 ring-brand-primary/10 transition-all duration-300 group-hover:scale-105 group-hover:ring-4 group-hover:ring-brand-accent/40 group-hover:shadow-brand">
            <img
              :src="entry.category.image_url || entry.products[0]?.get_thumbnail || entry.products[0]?.get_image || 'https://placehold.co/400'"
              :alt="entry.category.name"
              class="w-full h-full object-cover group-hover:scale-110 transition duration-500"
              loading="lazy"
            />
            <div class="absolute inset-0 rounded-full bg-gradient-to-t from-brand-primary/45 via-transparent to-transparent opacity-70 group-hover:opacity-30 transition duration-300"></div>
          </div>
          <div class="text-center">
            <h3 class="font-bold text-sm text-brand-primary leading-tight">{{ entry.category.name }}</h3>
            <p class="text-xs text-gray-400">{{ entry.category.product_count }} items</p>
          </div>
        </router-link>
      </div>
    </section>

    <!-- ===== Latest products (New Arrivals) ===== -->
    <section id="latest-products" v-reveal class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-10 pb-4">
      <div class="flex flex-col md:flex-row justify-between items-start md:items-end gap-3 mb-6">
        <div>
          <p class="text-[11px] uppercase tracking-[0.3em] text-brand-accent font-bold mb-1.5">Just landed</p>
          <h2 class="text-2xl sm:text-3xl font-extrabold tracking-tight">{{ categoryTitle }}</h2>
          <p class="text-gray-500 text-sm mt-1">Freshly added pieces from our design room.</p>
        </div>
        <div class="flex items-center gap-4">
          <router-link to="/new-arrivals" class="text-sm font-bold text-brand-accent hover:underline whitespace-nowrap">
            View all →
          </router-link>
          <router-link v-if="config.enableTrackingPage" to="/order-history" class="text-sm font-semibold underline text-gray-500 hover:text-gray-800 whitespace-nowrap">
            Track order
          </router-link>
        </div>
      </div>

      <div v-if="isLoading" class="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4 sm:gap-5">
        <div v-for="i in 8" :key="'sk-'+i" class="rounded-2xl overflow-hidden border border-gray-100 bg-white">
          <div class="aspect-[3/4] bg-gray-100 animate-pulse"></div>
          <div class="p-3.5 space-y-2">
            <div class="h-3.5 bg-gray-100 rounded animate-pulse w-3/4"></div>
            <div class="h-3.5 bg-gray-100 rounded animate-pulse w-1/2"></div>
          </div>
        </div>
      </div>
      <div v-else-if="products.length === 0" class="text-center py-12 text-gray-500 border border-dashed rounded-2xl bg-gray-50/60">No items found in this section yet.</div>
      <div v-else class="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4 sm:gap-5">
        <ProductCard v-for="product in products.slice(0, 8)" :key="product.id" :product="product" />
      </div>
    </section>

    <!-- ===== Social Live Feed — Facebook-synced drops ===== -->
    <section v-if="isHomePage" v-reveal class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
      <div class="relative overflow-hidden rounded-3xl bg-gradient-to-br from-[#0b2a5b] via-[#123c85] to-[#1877F2] text-white p-6 sm:p-8">
        <div class="absolute -top-16 -right-16 w-64 h-64 rounded-full bg-white/10 blur-2xl pointer-events-none"></div>
        <div class="absolute -bottom-20 -left-10 w-72 h-72 rounded-full bg-sky-300/20 blur-2xl pointer-events-none"></div>
        <div class="relative flex flex-col md:flex-row md:items-end justify-between gap-4 mb-6">
          <div>
            <p class="inline-flex items-center gap-2 text-[11px] font-extrabold uppercase tracking-[0.25em] bg-white/15 px-3 py-1.5 rounded-full mb-3">
              <span class="w-2 h-2 rounded-full bg-emerald-300 animate-pulse"></span>
              Social live feed
            </p>
            <h2 class="text-2xl sm:text-3xl font-extrabold tracking-tight">Fresh from Facebook</h2>
            <p class="text-blue-100 text-sm mt-1 max-w-lg">New drops sync automatically from our Facebook Page.</p>
          </div>
          <div class="flex items-center gap-3">
            <a v-if="facebookUrl" :href="facebookUrl" target="_blank" rel="noopener" class="text-sm font-bold bg-white text-[#1877F2] px-4 py-2.5 rounded-full hover:bg-blue-50 transition shadow">Follow Page ↗</a>
            <router-link to="/new-arrivals" class="text-sm font-bold text-white underline underline-offset-4 whitespace-nowrap">Shop all →</router-link>
          </div>
        </div>
        <div v-if="socialLoading" class="relative grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4">
          <div v-for="i in 4" :key="'soc-sk-'+i" class="rounded-2xl overflow-hidden bg-white/10">
            <div class="aspect-[3/4] bg-white/15 animate-pulse"></div>
          </div>
        </div>
        <div v-else-if="socialProducts.length" class="relative grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4">
          <ProductCard v-for="product in socialProducts" :key="'soc-'+product.id" :product="product" />
        </div>
        <div v-else class="relative text-center py-10 px-6 rounded-2xl bg-white/10 border border-white/15">
          <p class="font-bold text-lg">No Facebook drops yet</p>
          <p class="text-blue-100 text-sm mt-1 mb-4">Connect the Page in Admin → Store settings, then sync.</p>
          <router-link to="/new-arrivals" class="inline-block text-sm font-bold bg-white text-[#1877F2] px-5 py-2.5 rounded-full shadow">Browse new arrivals</router-link>
        </div>
      </div>
    </section>

    <!-- ===== Value props — compact trust strip ===== -->
    <section v-if="isHomePage" v-reveal class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
      <div class="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <div v-for="prop in valueProps" :key="prop.title" class="flex items-center gap-3 bg-brand-muted/60 border border-gray-100 rounded-2xl px-4 py-3.5">
          <span class="w-10 h-10 shrink-0 rounded-xl bg-white shadow-sm flex items-center justify-center text-brand-accent" v-html="prop.icon"></span>
          <span class="min-w-0">
            <span class="block text-[13px] font-extrabold text-slate-900 leading-tight">{{ prop.title }}</span>
            <span class="block text-[11px] text-gray-500 leading-tight truncate">{{ prop.sub }}</span>
          </span>
        </div>
      </div>
    </section>

    <!-- ===== Category-wise shopping sections (homepage only) ===== -->
    <div v-if="isHomePage && showcase.length" class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-10 space-y-12">
      <section v-for="entry in showcase" :key="'sec-' + entry.category.id" v-reveal>
        <div class="flex items-end justify-between mb-6">
          <div class="min-w-0">
            <h2 class="text-2xl font-bold tracking-tight mb-1">{{ entry.category.name }}</h2>
            <p v-if="entry.category.description" class="text-gray-500 text-sm max-w-xl">{{ entry.category.description }}</p>
          </div>
          <router-link :to="`/category/${entry.category.slug}`" class="text-sm font-semibold text-brand-accent underline decoration-brand-accent/40 hover:decoration-brand-accent whitespace-nowrap ml-4">
            View all →
          </router-link>
        </div>
        <div v-if="entry.products.length === 0" class="text-gray-400 text-sm py-6">No items in this category yet.</div>
        <div v-else class="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4 sm:gap-6">
          <ProductCard
            v-for="product in entry.products"
            :key="product.id"
            :product="product"
          />
        </div>
      </section>
    </div>

  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount, watch } from 'vue'
import { useRoute } from 'vue-router'
import axios from 'axios'
import Hero3D from '../components/Hero3D.vue'
import ProductCard from '../components/ProductCard.vue'
import { BRAND_CONFIG } from '../brand.config.js'
import { useCartStore } from '../stores/cart'
import { useSiteStore } from '../stores/site'
import { formatProductPrice } from '../utils/pricing.js'

const route = useRoute()
const cartStore = useCartStore()
const siteStore = useSiteStore()
const config = ref(BRAND_CONFIG)
const products = ref([])
const isLoading = ref(true)
const categorySlug = ref(route.params.category_slug || '')
const categoryTitle = ref('New Arrivals')
const heroSlides = ref([])
const showcase = ref([])
const socialProducts = ref([])
const socialLoading = ref(false)

// Trust strip under the social feed.
const valueProps = [
  { title: 'Fast Shipping', sub: 'Worldwide delivery', icon: '<svg class="w-5 h-5" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M3 7h11v10H3zM14 10h4l3 3v4h-7z"/><circle cx="7" cy="17.5" r="1.8"/><circle cx="17" cy="17.5" r="1.8"/></svg>' },
  { title: 'Secure Payment', sub: 'Stripe · PayPal · WhatsApp', icon: '<svg class="w-5 h-5" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M12 3l7 3v5c0 5-3.5 8-7 9-3.5-1-7-4-7-9V6z"/><path stroke-linecap="round" stroke-linejoin="round" d="M9 12l2 2 4-4"/></svg>' },
  { title: 'Easy Returns', sub: '7-day easy exchange', icon: '<svg class="w-5 h-5" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M4 9a8 8 0 0114-3l2 2M20 15a8 8 0 01-14 3l-2-2"/><path stroke-linecap="round" stroke-linejoin="round" d="M20 4v4h-4M4 20v-4h4"/></svg>' },
  { title: 'Live on Facebook', sub: 'New posts → products', icon: '<svg class="w-5 h-5" fill="currentColor" viewBox="0 0 24 24"><path d="M24 12.07C24 5.4 18.63 0 12 0S0 5.4 0 12.07C0 18.1 4.39 23.1 10.13 24v-8.44H7.08v-3.49h3.05V9.41c0-3.02 1.79-4.69 4.53-4.69 1.31 0 2.68.24 2.68.24v2.97h-1.51c-1.49 0-1.96.93-1.96 1.89v2.25h3.33l-.53 3.49h-2.8V24C19.61 23.1 24 18.1 24 12.07z"/></svg>' },
]

const facebookUrl = computed(() => siteStore.facebookPageUrl || '')

// 🌟 FIX: Computed property to detect Home Page
const isHomePage = computed(() => route.path === '/')

const currentSlide = ref(0)
let sliderInterval = null

const isInternalLink = (link) => {
  if (!link) return false
  return link.startsWith('/') || link.startsWith('#')
}

// Scroll-reveal directive: elements start hidden and lift in
// when they enter the viewport. Optional value = stagger delay (ms).
const vReveal = {
  mounted(el, binding) {
    el.classList.add('reveal-init')
    if (typeof binding.value === 'number') {
      el.style.transitionDelay = `${binding.value}ms`
    }
    const io = new IntersectionObserver((entries, observer) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          el.classList.remove('reveal-init')
          el.classList.add('reveal-in')
          observer.unobserve(el)
        }
      })
    }, { threshold: 0.08, rootMargin: '0px 0px -6% 0px' })
    el._revealIO = io
    io.observe(el)
  },
  unmounted(el) {
    el._revealIO?.disconnect()
    el._revealIO = null
  },
}

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

const fetchSocialFeed = async () => {
  if (!isHomePage.value) return
  socialLoading.value = true
  try {
    const res = await axios.get('/api/v1/social-feed/?limit=8')
    const data = res.data
    socialProducts.value = Array.isArray(data) ? data : (data.results || data.products || [])
  } catch (e) {
    console.error('Error loading social feed:', e)
    socialProducts.value = []
  } finally {
    socialLoading.value = false
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
  fetchSocialFeed()
  siteStore.fetchSettings()
  startImageRotation()
})

watch(() => route.params.category_slug, (newSlug) => {
  categorySlug.value = newSlug || ''
  fetchLatestProducts()
})

watch(() => route.path, (p) => {
  if (p === '/') { fetchShowcase(); fetchSocialFeed() }
})

onBeforeUnmount(() => {
  if (sliderInterval) clearInterval(sliderInterval)
})
</script>
