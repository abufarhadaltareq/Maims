<template>
  <div class="home-page font-brand text-brand-text">

    <!-- ===== Immersive, responsive hero gallery ===== -->
    <section
      v-if="isHomePage && siteStore.heroEnabled && heroSlides.length"
      class="hero-gallery relative isolate w-full overflow-hidden bg-[#10100f] text-white"
      :class="`hero-height-${siteStore.heroHeight}`"
      :style="{
        minHeight: heroHeightStyle,
        '--hero-accent': siteStore.heroAccent,
        '--hero-transition': `${siteStore.heroTransition}ms`,
        '--hero-zoom-scale': siteStore.heroKenburns ? 1.03 + siteStore.heroKenburns / 100 : 1,
      }"
      aria-label="Featured collections"
    >
      <div class="hero-gallery-backdrop absolute inset-0" aria-hidden="true">
        <template v-for="(slide, index) in heroSlides" :key="slide.id || index">
          <video
            v-if="slide.media_type === 'video' && slide.video_url"
            :src="slide.video_url"
            :poster="slide.image_url || undefined"
            class="hero-gallery-media absolute inset-0 h-full w-full object-cover"
            :class="{
              'hero-gallery-media-active': index === currentSlide,
              'hero-gallery-media-static': !siteStore.heroKenburns,
            }"
            :autoplay="index === currentSlide"
            muted loop playsinline preload="metadata"
            :aria-label="slide.title || `Hero video ${index + 1}`"
          ></video>
          <img
            v-else
            :src="slide.image_url"
            :alt="slide.title || `Hero image ${index + 1}`"
            class="hero-gallery-media absolute inset-0 h-full w-full object-cover"
            :class="{
              'hero-gallery-media-active': index === currentSlide,
              'hero-gallery-media-static': !siteStore.heroKenburns,
            }"
          />
        </template>
      </div>

      <Hero3D v-if="siteStore.hero3DEnabled" />
      <div class="hero-gallery-shade absolute inset-0" :style="{ opacity: siteStore.heroOverlay / 100 }" aria-hidden="true"></div>
      <div class="hero-gallery-grain absolute inset-0" aria-hidden="true"></div>
      <div v-if="siteStore.hero3DEnabled" class="hero-gallery-orbit absolute" aria-hidden="true"><span></span></div>

      <div class="hero-gallery-inner relative z-10 mx-auto flex h-full min-h-[inherit] max-w-[1600px] flex-col justify-end px-5 pb-6 pt-16 sm:px-10 sm:pb-9 lg:px-16 lg:pb-12">
        <div
          v-if="siteStore.heroShowCopy"
          class="hero-gallery-copy max-w-3xl"
          :class="{
            'hero-gallery-copy-shadow': siteStore.heroTextShadow,
            'hero-gallery-copy-glass': siteStore.heroGlassCards,
          }"
          aria-live="polite"
        >
          <p v-if="siteStore.heroEyebrow" class="mb-4 flex items-center gap-3 text-[10px] font-semibold uppercase tracking-[0.32em] text-white/80 sm:text-xs">
            <span class="h-px w-8 bg-[var(--hero-accent)]"></span>
            {{ siteStore.storeName }} <span class="text-[var(--hero-accent)]">/</span> {{ siteStore.heroEyebrow }}
          </p>
          <Transition name="hero-copy" mode="out-in">
            <div :key="currentSlide">
              <p v-if="currentHeroSlide.badge_text" class="mt-4 inline-flex border border-white/35 bg-black/20 px-3 py-1.5 text-[10px] font-semibold uppercase tracking-[0.2em] text-white/90 backdrop-blur-sm sm:text-xs">
                {{ currentHeroSlide.badge_text }}
              </p>
              <h1 class="max-w-3xl font-brand text-4xl font-medium leading-[1.03] tracking-[-0.045em] text-white sm:text-6xl lg:text-7xl xl:text-[5.5rem]">
                {{ currentHeroSlide.title || config.heroBannerTitle }}
              </h1>
              <p v-if="currentHeroSlide.subtitle || config.heroBannerSubtitle" class="mt-4 max-w-xl text-sm leading-relaxed text-white/80 sm:mt-6 sm:text-base lg:text-lg">
                {{ currentHeroSlide.subtitle || config.heroBannerSubtitle }}
              </p>
              <a
                v-if="currentHeroSlide.button_text"
                :href="currentHeroSlide.button_link || '#latest-products'"
                class="group mt-6 inline-flex min-h-12 items-center gap-5 border border-white/70 bg-white px-5 py-3 text-xs font-bold uppercase tracking-[0.16em] text-black transition hover:border-[var(--hero-accent)] hover:bg-[var(--hero-accent)] sm:mt-8 sm:px-7"
              >
                {{ currentHeroSlide.button_text }}
                <span class="text-lg leading-none transition-transform group-hover:translate-x-1" aria-hidden="true">→</span>
              </a>
            </div>
          </Transition>
        </div>

        <div v-if="siteStore.heroShowProgress || (siteStore.heroShowNavigation && heroSlides.length > 1)" class="hero-gallery-footer mt-9 flex items-end justify-between gap-5 sm:mt-12">
          <div v-if="siteStore.heroShowProgress" class="flex min-w-0 flex-1 items-center gap-4 sm:gap-6">
            <div class="hero-gallery-progress h-px max-w-48 flex-1 bg-white/50 sm:max-w-64" aria-hidden="true">
              <span :style="{ width: `${((currentSlide + 1) / heroSlides.length) * 100}%` }"></span>
            </div>
          </div>

          <div v-if="siteStore.heroShowNavigation && heroSlides.length > 1" class="flex max-w-[68vw] shrink-0 items-center gap-2 overflow-x-auto sm:max-w-none sm:gap-3">
            <button
              v-for="(item, index) in heroSlides"
              :key="item.id || index"
              @click="goToSlide(index)"
              class="hero-gallery-dot flex h-9 w-9 items-center justify-center rounded-full transition sm:h-10 sm:w-10"
              :class="index === currentSlide ? 'border border-white bg-white' : 'border border-white/50 bg-black/15 hover:border-white hover:bg-white/25'"
              :aria-label="`Show slide ${index + 1}: ${item.title || 'Featured collection'}`"
              :aria-current="index === currentSlide ? 'true' : undefined"
            ></button>
            <span class="mx-1 hidden h-7 w-px bg-white/30 sm:block" aria-hidden="true"></span>
            <button
              @click="previousSlide"
              class="hero-gallery-arrow hidden h-10 w-10 items-center justify-center rounded-full border border-white/40 text-xl transition hover:border-[var(--hero-accent)] hover:bg-[var(--hero-accent)] hover:text-black sm:flex"
              aria-label="Previous hero slide"
            >←</button>
            <button
              @click="nextSlide"
              class="hero-gallery-arrow flex h-10 w-10 items-center justify-center rounded-full border border-white/70 text-xl transition hover:border-[var(--hero-accent)] hover:bg-[var(--hero-accent)] hover:text-black sm:h-12 sm:w-12"
              aria-label="Next hero slide"
            >→</button>
          </div>
        </div>
      </div>
    </section>

    <nav
      v-if="isHomePage && mainCategories.length"
      aria-label="Main categories"
      class="mx-auto mt-4 max-w-[1500px] px-4 py-6 sm:mt-6 sm:px-7 sm:py-8"
    >
      <div class="relative mx-auto" :class="mainCategories.length >= 5 ? 'sm:max-w-[700px]' : ''">
        <button
          v-if="mainCategories.length > 1"
          @click="scrollMainCategories(-1)"
          aria-label="Previous main categories"
          class="absolute left-1 top-1/2 z-10 flex h-9 w-9 -translate-y-1/2 items-center justify-center border border-black/20 bg-white hover:bg-black hover:text-white sm:left-2"
          :class="mainCategories.length >= 5 ? 'sm:flex' : 'sm:hidden'"
        >
          ←
        </button>
        <div
          ref="mainCategoriesTrack"
          class="no-scrollbar flex snap-x snap-mandatory gap-x-5 overflow-x-auto scroll-smooth px-8 sm:gap-x-9 sm:px-0"
          :class="mainCategories.length >= 5 ? 'sm:flex-nowrap sm:justify-start sm:px-12' : 'sm:flex-wrap sm:justify-center sm:overflow-visible'"
        >
          <router-link
            v-for="category in mainCategories"
            :key="'main-category-' + category.id"
            :to="`/category/${category.slug}`"
            class="group flex w-24 flex-none snap-start flex-col items-center gap-2.5 text-center sm:w-28 sm:gap-3"
          >
            <span class="flex h-20 w-20 items-center justify-center overflow-hidden rounded-full border border-black/15 bg-gray-100 transition group-hover:border-black group-hover:ring-2 group-hover:ring-black/10 sm:h-24 sm:w-24">
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
        </div>
        <button
          v-if="mainCategories.length > 1"
          @click="scrollMainCategories(1)"
          aria-label="Next main categories"
          class="absolute right-1 top-1/2 z-10 flex h-9 w-9 -translate-y-1/2 items-center justify-center border border-black/20 bg-white hover:bg-black hover:text-white sm:right-2"
          :class="mainCategories.length >= 5 ? 'sm:flex' : 'sm:hidden'"
        >
          →
        </button>
      </div>
    </nav>

    <section v-if="isHomePage" id="latest-products" class="mx-auto max-w-[1500px] px-4 pb-7 sm:px-7 sm:pb-10">
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
      <div v-else-if="products.length" ref="newArrivalsTrack" class="no-scrollbar flex snap-x snap-mandatory gap-3 overflow-x-auto pb-2">
        <ProductCard
          v-for="product in products.slice(0, 12)"
          :key="product.id"
          :product="product"
          class="w-[calc(50%-6px)] shrink-0 snap-start sm:w-[calc(33.333%-8px)] lg:w-[calc(25%-9px)] xl:w-[calc(20%-10px)]"
        />
      </div>
      <p v-else class="py-8 text-sm text-gray-500">No new arrivals yet.</p>
    </section>

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
              class="absolute inset-0 h-full w-full object-cover object-center"
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
import Hero3D from '../components/Hero3D.vue'
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
const mainCategoriesTrack = ref(null)
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
const currentHeroSlide = computed(() => heroSlides.value[currentSlide.value] || {})
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

const scrollMainCategories = (direction) => {
  mainCategoriesTrack.value?.scrollBy({
    left: direction * mainCategoriesTrack.value.clientWidth * 0.8,
    behavior: 'smooth',
  })
}

const goToSlide = (index) => {
  currentSlide.value = (index + heroSlides.value.length) % heroSlides.value.length
  startImageRotation() // reset timer on manual click
}

const nextSlide = () => goToSlide(currentSlide.value + 1)
const previousSlide = () => goToSlide(currentSlide.value - 1)

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
    categoryTitle.value = categorySlug.value ? categorySlug.value.replace(/-/g, ' ') : 'New Arrivals'
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

watch(() => siteStore.heroRotation, startImageRotation)

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

<style scoped>
.hero-gallery {
  perspective: 1400px;
}

.hero-gallery-backdrop {
  z-index: 0;
  transform-style: preserve-3d;
}

.hero-gallery-media {
  opacity: 0;
  transform: scale(1.03);
  transition: opacity var(--hero-transition, 1100ms) ease;
}

.hero-gallery-media-active {
  opacity: 1;
  animation: hero-gallery-zoom 16s ease-out both;
}

.hero-gallery-media-static.hero-gallery-media-active {
  animation: none;
  transform: none;
}

.hero-gallery-shade {
  z-index: 2;
  background:
    linear-gradient(90deg, rgba(0, 0, 0, 0.78) 0%, rgba(0, 0, 0, 0.48) 43%, rgba(0, 0, 0, 0.08) 100%),
    linear-gradient(0deg, rgba(0, 0, 0, 0.58) 0%, transparent 52%);
  transition: opacity 400ms ease;
}

.hero-gallery-grain {
  z-index: 3;
  pointer-events: none;
  opacity: 0.14;
  background-image: radial-gradient(rgba(255, 255, 255, 0.45) 0.5px, transparent 0.7px);
  background-size: 4px 4px;
  mix-blend-mode: soft-light;
}

.hero-gallery-orbit {
  z-index: 4;
  top: -34%;
  right: -9%;
  width: min(57vw, 880px);
  aspect-ratio: 1;
  border: 1px solid color-mix(in srgb, var(--hero-accent) 42%, transparent);
  border-radius: 50%;
  transform: rotateX(68deg) rotateZ(-24deg);
  animation: hero-orbit-drift 18s ease-in-out infinite alternate;
  pointer-events: none;
}

.hero-gallery-orbit::before,
.hero-gallery-orbit::after,
.hero-gallery-orbit span {
  position: absolute;
  inset: 9%;
  border: 1px solid color-mix(in srgb, var(--hero-accent) 20%, transparent);
  border-radius: 50%;
  content: "";
}

.hero-gallery-orbit::before {
  inset: 20%;
  transform: rotateY(62deg);
}

.hero-gallery-orbit::after {
  inset: 31%;
  transform: rotateY(-62deg);
}

.hero-gallery-orbit span {
  inset: 4%;
  transform: rotateX(90deg);
}

.hero-gallery-inner {
  min-height: inherit;
}

.hero-gallery-copy-shadow h1 {
  text-shadow: 0 3px 30px rgba(0, 0, 0, 0.38);
}

.hero-gallery-copy-glass {
  padding: clamp(0rem, 2vw, 1.75rem);
  border: 1px solid rgba(255, 255, 255, 0.12);
  background: linear-gradient(115deg, rgba(0, 0, 0, 0.28), rgba(0, 0, 0, 0.04));
  backdrop-filter: blur(2px);
}

.hero-gallery-progress {
  overflow: hidden;
}

.hero-gallery-progress span {
  display: block;
  height: 100%;
  background: #fff;
  transition: width 450ms ease;
}

.hero-gallery-dot::before {
  width: 0.45rem;
  height: 0.45rem;
  border-radius: 9999px;
  background: #fff;
  content: "";
}

.hero-gallery-dot[aria-current="true"]::before {
  background: #111;
}

.hero-copy-enter-active,
.hero-copy-leave-active {
  transition: opacity 260ms ease, transform 260ms ease;
}

.hero-copy-enter-from {
  opacity: 0;
  transform: translateY(14px);
}

.hero-copy-leave-to {
  opacity: 0;
  transform: translateY(-8px);
}

@keyframes hero-gallery-zoom {
  from {
    transform: scale(1.03);
  }
  to {
    transform: scale(var(--hero-zoom-scale, 1.15)) translate3d(-1%, -0.5%, 0);
  }
}

@keyframes hero-orbit-drift {
  from {
    transform: rotateX(68deg) rotateZ(-24deg) translate3d(0, 0, 0);
  }
  to {
    transform: rotateX(68deg) rotateZ(-9deg) translate3d(-1%, 2%, 35px);
  }
}

@media (min-width: 768px) {
  .hero-gallery.hero-height-medium {
    min-height: min(70svh, 720px) !important;
  }

  .hero-gallery.hero-height-tall {
    min-height: min(84svh, 900px) !important;
  }

  .hero-gallery.hero-height-full {
    min-height: min(94svh, 1000px) !important;
  }

  .hero-gallery-inner {
    padding-bottom: clamp(2.5rem, 7vh, 5rem);
  }
}

@media (max-width: 639px) {
  .hero-gallery-orbit {
    top: -10%;
    right: -42%;
    width: 100vw;
    opacity: 0.55;
  }

  .hero-gallery-footer {
    align-items: center;
  }
}

@media (prefers-reduced-motion: reduce) {
  .hero-gallery-media-active,
  .hero-gallery-orbit {
    animation: none;
  }

  .hero-gallery-media,
  .hero-gallery-progress span,
  .hero-copy-enter-active,
  .hero-copy-leave-active {
    transition: none;
  }
}
</style>
