<template>
  <div class="home-page font-brand text-brand-text">

    <!-- ===== Hero — compact stylish gallery with sliding dots ===== -->
    <div
      v-if="isHomePage && siteStore.heroEnabled && heroSlides.length"
      class="hero-section relative w-full overflow-hidden"
      :style="{ minHeight: heroHeightStyle }"
    >
      <div class="absolute inset-x-0 top-0 bottom-0 overflow-hidden border-y border-black/10 bg-black sm:inset-x-5 sm:border">
      <template v-for="(slide, index) in heroSlides" :key="slide.id || index">
        <video
          v-if="slide.media_type === 'video' && slide.video_url"
          :src="slide.video_url"
          :poster="slide.image_url || undefined"
          class="absolute inset-0 h-full w-full object-cover transition-opacity duration-700"
          :class="index === currentSlide ? 'opacity-100 z-10' : 'opacity-0 z-0'"
          :autoplay="index === currentSlide"
          muted loop playsinline preload="metadata"
          :aria-label="slide.title || `Hero video ${index + 1}`"
        ></video>
        <img
          v-else
          :src="slide.image_url"
          :alt="slide.title || `Hero image ${index + 1}`"
          class="absolute inset-0 h-full w-full object-cover transition-opacity duration-700"
          :class="index === currentSlide ? 'opacity-100 z-10 animate-kenburns' : 'opacity-0 z-0'"
          :style="{ animationDuration: (siteStore.heroKenburns / 12) + 's' }"
        />
      </template>

      <!-- Sliding dots — one per image -->
      <div v-if="heroSlides.length > 1" class="absolute bottom-4 left-1/2 -translate-x-1/2 z-20 flex items-center justify-center gap-2 border border-white/40 bg-black/60 px-3 py-2">
        <button
          v-for="(item, index) in heroSlides"
          :key="item.id || index"
          @click="goToSlide(index)"
          class="h-2 rounded-full transition-all duration-300 overflow-hidden"
          :class="index === currentSlide ? 'w-8' : 'w-2 hover:bg-white/70'"
          :style="index === currentSlide ? { background: '#fff' } : { background: 'rgba(255,255,255,0.55)' }"
          :aria-label="`Go to slide ${index + 1}`"
        >
        </button>
      </div>
      </div>
    </div>

    <nav
      v-if="isHomePage && mainCategories.length"
      aria-label="Main categories"
      class="mx-auto flex max-w-[1500px] flex-wrap items-start justify-center gap-x-5 gap-y-4 px-4 py-5 sm:gap-x-8 sm:gap-y-5 sm:px-7 sm:py-6"
    >
      <router-link
        v-for="category in mainCategories"
        :key="'main-category-' + category.id"
        :to="`/category/${category.slug}`"
        class="group flex w-20 flex-col items-center gap-2 text-center sm:w-24"
      >
        <span class="flex h-16 w-16 items-center justify-center overflow-hidden rounded-full border border-black/15 bg-gray-100 transition group-hover:border-black group-hover:ring-2 group-hover:ring-black/10 sm:h-20 sm:w-20">
          <img
            v-if="category.image_url || category.children?.find((child) => child.image_url)?.image_url"
            :src="category.image_url || category.children.find((child) => child.image_url).image_url"
            :alt="category.name"
            class="h-full w-full object-cover object-center transition-transform duration-300 group-hover:scale-105"
            loading="lazy"
          />
          <span v-else class="text-xl font-medium text-gray-500">{{ category.name.slice(0, 1) }}</span>
        </span>
        <span class="text-xs font-semibold uppercase tracking-wide text-black sm:text-sm">{{ category.name }}</span>
      </router-link>
    </nav>

    <section v-if="isHomePage && showcase.length" v-reveal class="mx-auto max-w-[1500px] px-4 py-7 sm:px-7 sm:py-10">
      <h2 class="mb-4 border-b border-black pb-3 text-xl font-semibold tracking-tight sm:mb-6 sm:text-2xl">Shop by Category</h2>
      <div class="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
        <router-link
          v-for="(entry, i) in showcase"
          :key="'category-' + entry.category.id"
          :to="`/category/${entry.category.slug}`"
          v-reveal="i * 70"
          class="group flex min-w-0 flex-col"
        >
          <div class="relative aspect-[4/5] w-full overflow-hidden bg-gray-100">
            <img
              :src="entry.category.image_url || entry.products[0]?.get_thumbnail || entry.products[0]?.get_image || 'https://placehold.co/600x750?text=Category'"
              :alt="entry.category.name"
              class="h-full w-full object-contain object-center"
              loading="lazy"
            />
          </div>
          <div class="flex items-center justify-between gap-2 pt-3">
            <h3 class="truncate text-sm font-medium text-black">{{ entry.category.name }}</h3>
            <span aria-hidden="true" class="text-base transition-transform group-hover:translate-x-1">→</span>
          </div>
        </router-link>
      </div>
    </section>

    <section v-if="isHomePage" id="latest-products" class="mx-auto max-w-[1500px] px-4 pb-10 sm:px-7 sm:pb-14">
      <div class="mb-4 flex items-center justify-between border-b border-black pb-3 sm:mb-6">
        <h2 class="text-xl font-semibold tracking-tight sm:text-2xl">New Arrivals</h2>
        <div class="flex items-center gap-2">
          <button @click="scrollNewArrivals(-1)" class="flex h-9 w-9 items-center justify-center border border-black/20 hover:bg-black hover:text-white" aria-label="Previous new arrivals">←</button>
          <button @click="scrollNewArrivals(1)" class="flex h-9 w-9 items-center justify-center border border-black/20 hover:bg-black hover:text-white" aria-label="Next new arrivals">→</button>
        </div>
      </div>
      <div v-if="isLoading" class="grid grid-cols-2 gap-3 sm:grid-cols-4 lg:grid-cols-5">
        <div v-for="i in 5" :key="i" class="aspect-[3/4] animate-pulse bg-gray-100"></div>
      </div>
      <div v-else-if="products.length" ref="newArrivalsTrack" class="flex snap-x snap-mandatory gap-3 overflow-x-auto pb-2 no-scrollbar">
        <ProductCard
          v-for="product in products.slice(0, 12)"
          :key="product.id"
          :product="product"
          class="w-[calc(50%-6px)] shrink-0 snap-start sm:w-[calc(33.333%-8px)] lg:w-[calc(25%-9px)] xl:w-[calc(20%-10px)]"
        />
      </div>
      <p v-else class="py-8 text-sm text-gray-500">No new arrivals yet.</p>
    </section>

    <!-- Category and collection browsing -->
    <section v-if="!isHomePage" id="latest-products" v-reveal class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-10 pb-4">
      <div class="flex flex-col md:flex-row justify-between items-start md:items-end gap-3 mb-6">
        <div>
          <p class="text-[11px] uppercase tracking-[0.3em] text-brand-accent font-bold mb-1.5">Just landed</p>
          <h2 class="text-2xl sm:text-3xl font-extrabold tracking-tight text-gradient-brand">{{ categoryTitle }}</h2>
          <p class="text-gray-500 text-sm mt-1">{{ products.length }} products</p>
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



  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount, watch } from 'vue'
import { useRoute } from 'vue-router'
import axios from 'axios'
import ProductCard from '../components/ProductCard.vue'
import FilterSidebar from '../components/FilterSidebar.vue'
import { BRAND_CONFIG } from '../brand.config.js'
import { useSiteStore } from '../stores/site'

const route = useRoute()
const siteStore = useSiteStore()
const config = ref(BRAND_CONFIG)
const products = ref([])
const isLoading = ref(true)
const categorySlug = ref(route.params.category_slug || '')
const categoryTitle = ref('New Arrivals')
const heroSlides = ref([])
const showcase = ref([])
const mainCategories = ref([])
const newArrivalsTrack = ref(null)

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
    const slides = Array.isArray(res.data) ? res.data.filter((s) => s.image_url || s.video_url) : []
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

const fetchMainCategories = async () => {
  if (!isHomePage.value) return
  try {
    const res = await axios.get('/api/v1/categories/?homepage=true')
    mainCategories.value = Array.isArray(res.data) ? res.data : []
  } catch (e) {
    console.error('Error loading main categories:', e)
    mainCategories.value = []
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
    case 'medium': return 'clamp(320px, 55svh, 620px)'
    case 'full': return 'min(82svh, 820px)'
    default: return 'clamp(360px, 68svh, 740px)'
  }
})

const scrollNewArrivals = (direction) => {
  newArrivalsTrack.value?.scrollBy({
    left: direction * newArrivalsTrack.value.clientWidth * 0.8,
    behavior: 'smooth',
  })
}

const goToSlide = (index) => {
  currentSlide.value = index
  startImageRotation() // reset timer on manual click
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
  fetchMainCategories()
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
  if (p === '/') {
    fetchShowcase()
    fetchMainCategories()
  }
})

onBeforeUnmount(() => {
  if (sliderInterval) clearInterval(sliderInterval)
})
</script>
