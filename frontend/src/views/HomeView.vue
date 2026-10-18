<template>
  <div class="home-page font-brand text-brand-text">

    <!-- ===== Hero — compact stylish gallery with sliding dots ===== -->
    <div
      v-if="isHomePage && siteStore.heroEnabled && heroSlides.length"
      class="hero-section relative w-full overflow-hidden"
      :style="{ minHeight: heroHeightStyle }"
    >
      <div class="absolute inset-x-3 sm:inset-x-6 lg:inset-x-10 top-3 sm:top-4 bottom-3 sm:bottom-4 overflow-hidden rounded-2xl sm:rounded-3xl bg-slate-950 shadow-xl shadow-slate-900/30 ring-1 ring-black/10">
      <!-- Animated 3D Background component (admin-controlled transparency) -->
      <Hero3D v-if="siteStore.hero3DEnabled" />

      <div
        v-for="(slide, index) in heroSlides"
        :key="slide.id || index"
        class="absolute inset-0 bg-cover bg-center transition-opacity ease-in-out"
        :class="index === currentSlide ? 'opacity-100 z-10 animate-kenburns' : 'opacity-0 z-0'"
        :style="{ backgroundImage: `url(${slide.image_url})`, animationDuration: (siteStore.heroKenburns / 12) + 's' }"
      ></div>

      <!-- Sliding dots — one per image -->
      <div v-if="heroSlides.length > 1" class="absolute bottom-4 left-1/2 -translate-x-1/2 z-20 flex items-center justify-center gap-2 rounded-full bg-black/35 px-3 py-2 backdrop-blur-sm">
        <button
          v-for="(item, index) in heroSlides"
          :key="item.id || index"
          @click="goToSlide(index)"
          class="h-2 rounded-full transition-all duration-300 overflow-hidden"
          :class="index === currentSlide ? 'w-8' : 'w-2 hover:bg-white/70'"
          :style="index === currentSlide ? { background: 'var(--hero-accent, #0ea5e9)' } : { background: 'rgba(255,255,255,0.55)' }"
          :aria-label="`Go to slide ${index + 1}`"
        >
        </button>
      </div>
      </div>
    </div>

    <!-- ===== Shop by Category — round balls, directly under the hero ===== -->
    <section v-if="isHomePage && showcase.length" v-reveal class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-8 pb-4">
      <div class="text-center mb-8">
        <p class="text-[11px] uppercase tracking-[0.3em] text-brand-accent font-bold mb-2">Collections</p>
        <h2 class="text-3xl font-extrabold tracking-tight text-gradient-brand">Shop by Category</h2>
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
          <h2 class="text-2xl sm:text-3xl font-extrabold tracking-tight text-gradient-brand">{{ categoryTitle }}</h2>
          <p class="text-gray-500 text-sm mt-1">{{ products.length }} fresh pieces{{ brands.length ? ` · ${brands.length} brands` : '' }}</p>
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

      <!-- Favorite brands rail (deshi-besh style, homepage only) -->
      <div v-if="isHomePage && brands.length" class="mb-8">
        <h3 class="text-center text-2xl font-extrabold tracking-tight text-gradient-brand mb-5">Favorite Brands</h3>
        <div class="flex gap-4 overflow-x-auto no-scrollbar pb-2 snap-x">
          <button
            v-for="b in brands"
            :key="b.name"
            type="button"
            @click="searchBrand(b.name)"
            class="shrink-0 w-36 sm:w-44 snap-start group text-center"
          >
            <span class="block aspect-[3/4] rounded-2xl overflow-hidden bg-gray-100">
              <img :src="b.image || 'https://placehold.co/300x400'" :alt="b.name" class="w-full h-full object-cover group-hover:scale-105 transition duration-500" loading="lazy" />
            </span>
            <span class="block mt-2 text-[12px] font-medium tracking-[0.2em] uppercase">{{ b.name }}</span>
          </button>
        </div>
      </div>

      <!-- Deshi-besh style browsing layout: sticky filter sidebar + product grid. -->
      <div v-if="categorySlug" class="grid grid-cols-1 lg:grid-cols-[240px_1fr] gap-8 items-start">
        <div class="hidden lg:block sticky top-32 max-h-[calc(100vh-9rem)] overflow-y-auto pr-2">
          <FilterSidebar
            :sizes="facets.sizes" :colors="facets.colors" :lengths="facets.lengths" :fabrics="facets.fabrics"
            :selected="filters" :has-active="hasActiveFilters" :active-colors="filters.colors"
            @toggle-size="toggleFilter('sizes', $event)" @toggle-color="toggleFilter('colors', $event)"
            @toggle-length="toggleFilter('lengths', $event)" @toggle-fabric="toggleFilter('fabrics', $event)"
            @clear="clearFilters"
          />
        </div>
        <div class="min-w-0">
          <!-- Mobile filter toggle -->
          <button
            type="button" @click="mobileFilters = !mobileFilters"
            class="lg:hidden w-full mb-4 flex items-center justify-between border border-gray-200 rounded-xl px-4 py-3 text-sm font-bold"
          >
            <span>Filters{{ activeFilterCount ? ` (${activeFilterCount})` : '' }}</span>
            <span>{{ mobileFilters ? '−' : '+' }}</span>
          </button>
          <div v-show="mobileFilters" class="lg:hidden mb-4 border border-gray-100 rounded-2xl p-4">
            <FilterSidebar
              :sizes="facets.sizes" :colors="facets.colors" :lengths="facets.lengths" :fabrics="facets.fabrics"
              :selected="filters" :has-active="hasActiveFilters" :active-colors="filters.colors"
              @toggle-size="toggleFilter('sizes', $event)" @toggle-color="toggleFilter('colors', $event)"
              @toggle-length="toggleFilter('lengths', $event)" @toggle-fabric="toggleFilter('fabrics', $event)"
              @clear="clearFilters"
            />
          </div>

          <div v-if="isLoading" class="grid grid-cols-2 sm:grid-cols-3 gap-4 sm:gap-5">
            <div v-for="i in 8" :key="'sk-'+i" class="rounded-2xl overflow-hidden border border-gray-100 bg-white">
              <div class="aspect-[3/4] bg-gray-100 animate-pulse"></div>
              <div class="p-3.5 space-y-2">
                <div class="h-3.5 bg-gray-100 rounded animate-pulse w-3/4"></div>
                <div class="h-3.5 bg-gray-100 rounded animate-pulse w-1/2"></div>
              </div>
            </div>
          </div>
          <div v-else-if="products.length === 0" class="text-center py-12 text-gray-500 border border-dashed rounded-2xl bg-gray-50/60">
            <p class="font-bold text-slate-800">No matches for these filters</p>
            <p class="text-sm mt-1 mb-4">Try removing a size or color.</p>
            <button type="button" @click="clearFilters" class="text-sm font-bold bg-[var(--color-brand)] text-white px-5 py-2.5 rounded-full">Clear filters</button>
          </div>
          <div v-else class="grid grid-cols-2 sm:grid-cols-3 gap-4 sm:gap-5">
            <ProductCard v-for="product in products" :key="product.id" :product="product" />
          </div>
        </div>
      </div>
      <template v-else>
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
      </template>
    </section>



    <!-- ===== Category-wise shopping sections (homepage only) ===== -->
    <div v-if="isHomePage && showcase.length" class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-10 space-y-12">
      <section v-for="entry in showcase" :key="'sec-' + entry.category.id" v-reveal>
        <div class="flex items-end justify-between mb-6">
          <div class="min-w-0">
            <h2 class="text-2xl font-extrabold tracking-tight text-gradient-brand mb-1">{{ entry.category.name }}</h2>
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
import FilterSidebar from '../components/FilterSidebar.vue'
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
const brands = ref([])

// Deshi-besh style filters (category pages).
const filters = ref({ sizes: [], colors: [], lengths: [], fabrics: [] })
const facets = ref({ sizes: [], colors: [], lengths: [], fabrics: [] })
const mobileFilters = ref(false)
const hasActiveFilters = computed(() =>
  filters.value.sizes.length + filters.value.colors.length +
  filters.value.lengths.length + filters.value.fabrics.length > 0
)
const activeFilterCount = computed(() =>
  filters.value.sizes.length + filters.value.colors.length +
  filters.value.lengths.length + filters.value.fabrics.length
)

const toggleFilter = (key, value) => {
  const list = filters.value[key]
  const i = list.findIndex((v) => String(v).toLowerCase() === String(value).toLowerCase())
  if (i >= 0) list.splice(i, 1)
  else list.push(value)
  fetchLatestProducts()
}
const clearFilters = () => {
  filters.value = { sizes: [], colors: [], lengths: [], fabrics: [] }
  fetchLatestProducts()
}
const searchBrand = (name) => {
  // Brand rail shortcut: jump to the global search for that brand.
  window.location.href = `/search?q=${encodeURIComponent(name)}`
}


const facebookUrl = computed(() => siteStore.facebookPageUrl || '')

// 🌟 FIX: Computed property to detect Home Page
const isHomePage = computed(() => route.path === '/')

const currentSlide = ref(0)
let sliderInterval = null

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

const fetchBrands = async () => {
  if (!isHomePage.value) return
  try {
    const res = await axios.get('/api/v1/brands/?limit=12')
    brands.value = Array.isArray(res.data) ? res.data : []
  } catch (e) {
    brands.value = []
  }
}

const fetchFacets = async () => {
  if (!categorySlug.value) { facets.value = { sizes: [], colors: [], lengths: [], fabrics: [] }; return }
  try {
    const res = await axios.get(`/api/v1/facets/?category=${categorySlug.value}`)
    facets.value = { sizes: [], colors: [], lengths: [], fabrics: [], ...(res.data || {}) }
  } catch (e) {
    facets.value = { sizes: [], colors: [], lengths: [], fabrics: [] }
  }
}

const startImageRotation = () => {
  if (sliderInterval) clearInterval(sliderInterval)
  const interval = (siteStore.heroRotation || 5) * 1000
  sliderInterval = setInterval(() => {
    if (siteStore.heroAutoplay && heroSlides.value && heroSlides.value.length > 1) {
      currentSlide.value = (currentSlide.value + 1) % heroSlides.value.length
    }
  }, interval)
}

// Admin-controlled hero height: big gallery.
const heroHeightStyle = computed(() => {
  switch (siteStore.heroHeight) {
    case 'medium': return '68svh'
    case 'full': return '92svh'
    default: return '80svh'
  }
})

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
    const params = new URLSearchParams()
    if (categorySlug.value) params.set('category', categorySlug.value)
    const f = filters.value
    if (categorySlug.value && f.sizes.length) params.set('size', f.sizes.join(','))
    if (categorySlug.value && f.colors.length) params.set('color', f.colors.join(','))
    if (categorySlug.value && f.lengths.length) params.set('length', f.lengths.join(','))
    if (categorySlug.value && f.fabrics.length) params.set('fabric', f.fabrics.join(','))
    const qs = params.toString() ? `?${params.toString()}` : ''
    const response = await axios.get(`/api/v1/products/${qs}`)
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
  siteStore.fetchHero()
  siteStore.fetchSettings()
  fetchFacets()
  fetchLatestProducts()
  fetchShowcase()
  fetchBrands()
  startImageRotation()
})

watch(() => route.params.category_slug, (newSlug) => {
  categorySlug.value = newSlug || ''
  clearFiltersSilent()
  fetchFacets()
  fetchLatestProducts()
})

const clearFiltersSilent = () => {
  filters.value = { sizes: [], colors: [], lengths: [], fabrics: [] }
}

watch(() => route.path, (p) => {
  if (p === '/') { fetchShowcase() }
})

onBeforeUnmount(() => {
  if (sliderInterval) clearInterval(sliderInterval)
})
</script>
