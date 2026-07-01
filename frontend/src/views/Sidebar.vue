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
    <nav class="space-y-2">
      <div v-for="item in menuStructure" :key="item.name" class="border-b border-gray-50 pb-2 last:border-none">
        
        <!-- Parent Header Action Toggle -->
        <button
          @click="toggleCategory(item.name)"
          type="button"
          class="w-full flex items-center justify-between text-left px-3 py-2.5 rounded-xl text-slate-800 font-semibold text-sm hover:bg-slate-50 transition-all duration-200 group"
        >
          <div class="flex items-center gap-3">
            <span class="text-lg opacity-80 group-hover:scale-110 transition-transform">{{ item.icon }}</span>
            <span class="tracking-wide group-hover:text-black">{{ item.name }}</span>
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

    <!-- Additional Premium UI Modules (Standard for High-End E-commerce) -->
    <div class="mt-12 pt-6 border-t border-gray-100 space-y-6 px-2">
      <div>
        <h3 class="text-[10px] font-bold uppercase tracking-[0.25em] text-gray-400 mb-3">
          Customer Service
        </h3>
        <ul class="space-y-2 text-xs font-medium text-slate-500">
          <li><a href="#" class="hover:text-black transition-colors">Track Order</a></li>
          <li><a href="#" class="hover:text-black transition-colors">Worldwide Shipping</a></li>
          <li><a href="#" class="hover:text-black transition-colors">Easy Returns</a></li>
        </ul>
      </div>
    </div>
  </aside>
</template>

<script setup>
import { ref } from 'vue'

// Track active toggle states dynamically
const openCategories = ref({
  'Women Clothing': true,
  'Jewellery': false
})

const toggleCategory = (name) => {
  openCategories.value[name] = !openCategories.value[name]
}

// Structured tree cleanly wrapping your database slugs to look like LAAM
const menuStructure = ref([
  {
    name: 'Women Clothing',
    icon: '👗',
    badge: 'New',
    subcategories: [
      { name: 'Pakistani Pret', slug: 'pakistani' },
      { name: 'Jamdani Heritage', slug: 'jamdani' },
      { name: 'Stitched Luxury', slug: 'stiched' },
      { name: 'Unstitched Fabrics', slug: 'unstiched' }
    ]
  },
  {
    name: 'Jewellery',
    icon: '✨',
    subcategories: [
      { name: 'Necklaces & Sets', slug: 'jewelarry' }
    ]
  },
  {
    name: 'Ready To Ship',
    icon: '⚡',
    badge: 'Hot',
    subcategories: []
  }
])
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