<template>
  <aside class="w-64 bg-white border-r border-gray-100 min-h-screen px-4 py-6 font-brand">
    <!-- Top Branding / Heading Section -->
    <div class="mb-8 px-2 flex items-center justify-between">
      <h2 class="text-xs font-bold uppercase tracking-[0.25em] text-gray-400">
        Shop Collections
      </h2>
      <span class="bg-black text-[10px] font-bold text-white px-2 py-0.5 rounded-full uppercase tracking-wider">
        2026
      </span>
    </div>

    <!-- Navigation Tree Links -->
    <div v-if="loading" class="px-3 py-6 text-xs text-gray-400 font-medium">Loading collections…</div>
    <div v-else-if="loadError" class="px-3 py-4 text-xs text-red-500 bg-red-50 rounded-xl">
      Couldn't load categories. <button @click="fetchCategories" class="underline font-bold">Retry</button>
    </div>
    <nav v-else class="space-y-2">
      <router-link
        to="/"
        class="flex items-center gap-3 px-3 py-2.5 rounded-xl text-slate-800 font-semibold text-sm hover:bg-slate-50 transition-all"
      >
        <span class="text-lg">🛍️</span><span>All Products</span>
      </router-link>
      <div v-for="item in menuStructure" :key="item.slug || item.name" class="border-b border-gray-50 pb-2 last:border-none">
        
        <!-- Parent Header Action Toggle -->
        <button
          @click="toggleCategory(item.name)"
          type="button"
          class="w-full flex items-center justify-between text-left px-3 py-2.5 rounded-xl text-slate-800 font-semibold text-sm hover:bg-slate-50 transition-all duration-200 group"
        >
          <div class="flex items-center gap-3">
            <span class="text-lg opacity-80 group-hover:scale-110 transition-transform">{{ item.icon }}</span>
            <router-link v-if="item.slug" :to="`/category/${item.slug}`" @click.stop class="tracking-wide group-hover:text-black flex items-center gap-2">
              {{ item.name }}
              <span v-if="item.count" class="text-[10px] bg-gray-100 text-gray-500 px-1.5 py-0.5 rounded-full font-bold">{{ item.count }}</span>
            </router-link>
            <span v-else class="tracking-wide group-hover:text-black">{{ item.name }}</span>
          </div>
          
          <div class="flex items-center gap-2">
            <span v-if="item.badge" class="text-[9px] font-black uppercase bg-red-50 text-red-500 px-2 py-0.5 rounded-md tracking-wider">
              {{ item.badge }}
            </span>
            <span v-if="item.subcategories?.length" class="text-[10px] transition-transform duration-300 text-gray-400" :class="{ 'rotate-180 text-black': openCategories[item.name] }">
              ▼
            </span>
          </div>
        </button>

        <!-- Nested Accordion Child List -->
        <div v-if="item.subcategories?.length" 
             v-show="openCategories[item.name]" 
             class="mt-1 ml-9 pl-2 border-l border-gray-100 space-y-1 overflow-hidden transition-all duration-300">
          <router-link
            v-for="sub in item.subcategories"
            :key="sub.slug"
            :to="`/category/${sub.slug}`"
            class="block py-1.5 px-2 text-xs font-medium text-slate-500 hover:text-black hover:translate-x-1 transition-all duration-200 capitalize"
          >
            {{ sub.name }}
          </router-link>
        </div>
      </div>
    </nav>


  </aside>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import axios from 'axios'

const ICONS = ['👗', '✨', '🧥', '👜', '👟', '💎', '🧣', '👒', '🧵', '⚡']

// Track active toggle states dynamically
const openCategories = ref({})
const backendCategories = ref([])
const loading = ref(true)
const loadError = ref(false)

const toggleCategory = (name) => {
  openCategories.value[name] = !openCategories.value[name]
}

const iconFor = (index, name) => {
  const n = (name || '').toLowerCase()
  if (n.includes('jewel')) return '✨'
  if (n.includes('women') || n.includes('dress') || n.includes('cloth')) return '👗'
  if (n.includes('men')) return '🧥'
  if (n.includes('bag')) return '👜'
  if (n.includes('shoe')) return '👟'
  if (n.includes('ship') || n.includes('ready')) return '⚡'
  return ICONS[index % ICONS.length]
}

// Build menu from backend: top-level parents with nested children.
const fallbackMenu = [
  { name: 'Women Clothing', slug: '', icon: '👗', badge: 'New', count: 0, subcategories: [] },
  { name: 'Jewellery', slug: '', icon: '✨', badge: '', count: 0, subcategories: [] },
]

const menuStructure = computed(() => {
  if (!backendCategories.value.length) return fallbackMenu
  return backendCategories.value.map((cat, i) => ({
    name: cat.name,
    slug: cat.slug,
    icon: iconFor(i, cat.name),
    badge: i === 0 ? 'New' : '',
    count: cat.product_count || 0,
    subcategories: (cat.children || []).map((c) => ({ name: c.name, slug: c.slug })),
  }))
})

const fetchCategories = async () => {
  loading.value = true
  loadError.value = false
  try {
    const res = await axios.get('/api/v1/categories/')
    backendCategories.value = Array.isArray(res.data) ? res.data : []
    backendCategories.value.forEach((cat, i) => {
      if (i === 0 || (cat.children && cat.children.length)) openCategories.value[cat.name] = i === 0
    })
  } catch (e) {
    console.error('Sidebar categories failed:', e)
    loadError.value = true
  } finally {
    loading.value = false
  }
}

onMounted(fetchCategories)
</script>

<style scoped>
/* Scoped active state match for Vue Router link tree highlighting */
.router-link-active {
  color: #000000 !important;
  font-weight: 700;
}

/* Custom scrollbar hiding helper if needed for side scroll features */
.no-scrollbar::-webkit-scrollbar {
  display: none;
}
.no-scrollbar {
  -ms-overflow-style: none;
  scrollbar-width: none;
}
</style>