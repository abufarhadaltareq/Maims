<template>
  <!-- Aarong-style top category nav: replaces left sidebar, sits under header.
       The hover mega-menu only shows on large desktops (≥1400px) where all the
       category links (~1280px of them) fit without overflowing; below that the
       row would push the whole page into horizontal scroll (the dropdowns need
       overflow:visible, so the row itself can't be made scrollable). -->
  <nav class="bg-white border-t border-gray-100 hidden min-[1400px]:block">
    <div class="max-w-[1600px] mx-auto px-4 sm:px-6">
      <ul v-if="!loading && !loadError" class="flex items-center justify-center gap-7 lg:gap-9 h-11">
        <li>
          <router-link
            to="/"
            exact-active-class="nav-active"
            class="nav-link"
          >
            All Products
          </router-link>
        </li>
        <li
          v-for="item in menuStructure"
          :key="item.slug || item.name"
          class="relative group h-full flex items-center"
        >
          <router-link
            v-if="item.slug"
            :to="`/category/${item.slug}`"
            active-class="nav-active"
            class="nav-link flex items-center gap-1"
          >
            {{ item.name.toUpperCase() }}
            <span v-if="item.subcategories?.length" class="text-[9px] text-[var(--color-content-secondary)] group-hover:text-[var(--color-content)] transition-colors">▼</span>
          </router-link>
          <span v-else class="nav-link cursor-default">{{ item.name.toUpperCase() }}</span>

          <!-- Hover dropdown for subcategories -->
          <div
            v-if="item.subcategories?.length"
            class="invisible opacity-0 group-hover:visible group-hover:opacity-100 transition-all duration-200 absolute left-1/2 -translate-x-1/2 top-full min-w-[200px] bg-white border border-gray-100 shadow-xl rounded-b-xl py-2 z-50"
          >
            <router-link
              v-for="sub in item.subcategories"
              :key="sub.slug"
              :to="`/category/${sub.slug}`"
              class="block px-5 py-2 text-[13px] font-medium text-[var(--color-content-secondary)] hover:text-[var(--color-content)] hover:bg-gray-50 capitalize whitespace-nowrap"
            >
              {{ sub.name }}
            </router-link>
          </div>
        </li>
      </ul>
      <div v-else-if="loading" class="flex items-center justify-center gap-6 h-11 text-[12px] text-gray-400 font-medium uppercase tracking-wider">
        <span>Loading collections…</span>
      </div>
      <ul v-else class="flex items-center justify-center gap-7 h-11">
        <li v-for="name in fallbackNames" :key="name">
          <span class="nav-link cursor-default">{{ name }}</span>
        </li>
      </ul>
    </div>
  </nav>

  <!-- Mobile & tablet (<1400px): horizontally-scrollable row (no sidebar drawer).
       Self-scrolls instead of overflowing the page; edge fades hint that there
       are more categories to the right. Touch-friendly for tablets/phones. -->
  <nav class="relative bg-white border-t border-gray-100 hidden max-[1399px]:block">
    <div ref="scrollerRef" @scroll="onScroll" class="overflow-x-auto no-scrollbar overscroll-x-contain">
      <div class="flex items-center gap-5 px-4 h-11 w-max min-w-full">
        <router-link to="/" exact-active-class="nav-active" class="nav-link whitespace-nowrap">All</router-link>
        <template v-if="menuStructure.length">
          <router-link
            v-for="item in menuStructure"
            :key="item.slug || item.name"
            :to="item.slug ? `/category/${item.slug}` : '/'"
            active-class="nav-active"
            class="nav-link whitespace-nowrap"
          >
            {{ item.name.toUpperCase() }}
          </router-link>
        </template>
        <template v-else-if="loading">
          <span class="nav-link whitespace-nowrap text-gray-400">Loading…</span>
        </template>
        <template v-else>
          <span v-for="name in fallbackNames" :key="name" class="nav-link whitespace-nowrap">{{ name }}</span>
        </template>
      </div>
    </div>
    <!-- Right edge fade: signals the row scrolls (hidden once scrolled to end) -->
    <div
      v-if="scrollable && !scrolledToEnd"
      class="pointer-events-none absolute inset-y-0 right-0 w-10 bg-gradient-to-l from-white via-white/80 to-transparent"
      aria-hidden="true"
    ></div>
  </nav>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount, nextTick } from 'vue'
import axios from 'axios'

const backendCategories = ref([])
const loading = ref(true)
const loadError = ref(false)

const fallbackNames = ['WOMEN', 'MEN', 'KIDS', 'HOME DÉCOR', 'JEWELLERY']

const menuStructure = computed(() => {
  if (!backendCategories.value.length) return []
  return backendCategories.value.map((cat) => ({
    name: cat.name,
    slug: cat.slug,
    subcategories: (cat.children || []).map((c) => ({ name: c.name, slug: c.slug })),
  }))
})

// --- Mobile/tablet scroll-row state (drives the right-edge fade hint) ---
const scrollerRef = ref(null)
const scrollable = ref(false)
const scrolledToEnd = ref(true)

const updateScrollState = () => {
  const el = scrollerRef.value
  if (!el) return
  // 1px tolerance for sub-pixel rounding.
  const overflow = el.scrollWidth - el.clientWidth
  scrollable.value = overflow > 1
  scrolledToEnd.value = !scrollable.value || el.scrollLeft >= overflow - 1
}
const onScroll = () => updateScrollState()

let ro = null
const observeScroller = async () => {
  await nextTick()
  updateScrollState()
  if (scrollerRef.value && typeof ResizeObserver !== 'undefined') {
    ro?.disconnect()
    ro = new ResizeObserver(() => updateScrollState())
    ro.observe(scrollerRef.value)
  }
}

const fetchCategories = async () => {
  loading.value = true
  loadError.value = false
  try {
    const res = await axios.get('/api/v1/categories/')
    backendCategories.value = Array.isArray(res.data) ? res.data : []
  } catch (e) {
    console.error('CategoryNav categories failed:', e)
    loadError.value = true
  } finally {
    loading.value = false
    // Categories just rendered — re-measure the scroll row.
    observeScroller()
  }
}

onMounted(() => {
  fetchCategories()
  window.addEventListener('resize', updateScrollState)
})
onBeforeUnmount(() => {
  window.removeEventListener('resize', updateScrollState)
  ro?.disconnect()
})
</script>

<style scoped>
.nav-link {
  font-size: 13px;
  font-weight: 500;
  letter-spacing: 0.04em;
  color: #111;
  text-transform: uppercase;
  white-space: nowrap;
  padding: 4px 0;
  border-bottom: 2px solid transparent;
  transition: border-color 0.2s, color 0.2s;
}
.nav-link:hover {
  border-bottom-color: #111;
}
.nav-active {
  border-bottom-color: #111;
  font-weight: 700;
}
.no-scrollbar::-webkit-scrollbar {
  display: none;
}
.no-scrollbar {
  -ms-overflow-style: none;
  scrollbar-width: none;
}
</style>
