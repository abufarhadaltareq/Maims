<template>
  <div class="min-h-screen flex flex-col font-brand text-gray-900 bg-white">
    <!-- Header Block -->
    <header class="sticky top-0 z-50 bg-white border-b border-gray-100 px-6 py-3">
      <div class="max-w-[1600px] mx-auto flex items-center justify-between gap-8">
        
        <div class="flex items-center gap-4">
          <!-- Mobile Sidebar Toggle button -->
          <button @click="isSidebarOpen = !isSidebarOpen" class="lg:hidden p-2 text-gray-600 hover:bg-gray-100 rounded-lg">
            <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h16"></path>
            </svg>
          </button>
          <router-link to="/">
            <img src="./assets/logo.png" class="h-8 w-auto" alt="Brand Logo">
          </router-link>
        </div>

        <!-- Central Search Context -->
        <div class="flex-1 max-w-xl">
          <input 
            v-model="searchQuery" 
            @keyup.enter="performSearch" 
            placeholder="Search for products..." 
            class="w-full bg-gray-50 border border-gray-200 rounded-lg p-2.5 text-sm outline-none focus:border-black transition"
          >
        </div>
        
        <!-- Right Utility Actions -->
        <div class="flex items-center gap-6 text-sm">
          <!-- Currency Picker Element Matrix -->
          <div class="relative cursor-pointer select-none" @click.stop="isCurrencyOpen = !isCurrencyOpen">
            <p class="text-[9px] text-gray-400 font-bold uppercase tracking-wider">Deliver To / Currency</p>
            <p class="font-semibold text-gray-800 text-sm flex items-center gap-1">
               🇵🇹 PT / {{ cartStore.currentCurrency }} <span class="text-[10px] text-gray-400">▼</span>
            </p>
            
            <div v-if="isCurrencyOpen" class="absolute right-0 mt-2 bg-white border border-gray-100 shadow-xl rounded-xl w-32 z-50 py-1 overflow-hidden">
              <button @click.stop="setCurrency('EUR')" class="block w-full text-left px-4 py-2 hover:bg-gray-50 text-sm transition-colors">EUR (€)</button>
              <button @click.stop="setCurrency('PKR')" class="block w-full text-left px-4 py-2 hover:bg-gray-50 text-sm transition-colors">PKR (₨)</button>
              <button @click.stop="setCurrency('USD')" class="block w-full text-left px-4 py-2 hover:bg-gray-50 text-sm transition-colors">USD ($)</button>
              <button @click.stop="setCurrency('SEK')" class="block w-full text-left px-4 py-2 hover:bg-gray-50 text-sm transition-colors">SEK (kr)</button>
              <button @click.stop="setCurrency('BDT')" class="block w-full text-left px-4 py-2 hover:bg-gray-50 text-sm transition-colors">BDT (৳)</button>
            </div>
          </div>

          <!-- Dynamic Cart Node Counter Trigger -->
          <router-link to="/cart" class="relative text-gray-700 hover:text-black transition-colors">
            <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path d="M6 2L3 6v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V6l-3-4Z" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"></path>
              <path d="M3 6h18" stroke-width="2" stroke-linecap="round"></path>
              <path d="M16 10a4 4 0 0 1-8 0" stroke-width="2" stroke-linecap="round"></path>
            </svg>
            <span v-if="cartStore.cartTotalLength > 0" class="absolute -top-2 -right-2 bg-black text-white text-[10px] w-5 h-5 flex items-center justify-center rounded-full font-bold transform scale-90">
              {{ cartStore.cartTotalLength }}
            </span>
          </router-link>
        </div>
      </div>
    </header>

    <!-- Content Workspace Wrapper Frame Layout -->
    <div class="flex flex-1 max-w-[1600px] mx-auto w-full relative">
      
      <!-- Premium LAAM-Inspired Responsive Sidebar -->
      <Sidebar 
        :class="[
          'transition-all duration-300 lg:block flex-shrink-0', 
          isSidebarOpen ? 'fixed inset-y-0 left-0 z-40 w-64 shadow-2xl bg-white border-r border-gray-100 pt-20 lg:pt-0' : 'hidden'
        ]"
        @close-mobile-menu="isSidebarOpen = false"
      />

      <!-- Backdrop Overlay for Mobile Navigation Drawers -->
      <div 
        v-if="isSidebarOpen" 
        @click="isSidebarOpen = false" 
        class="fixed inset-0 bg-black/20 backdrop-blur-sm z-30 lg:hidden"
      ></div>

      <!-- Main Display Route Target Space Slot -->
      <main class="flex-1 p-8 min-w-0 bg-white">
        <router-view />
      </main>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useCartStore } from './stores/cart'
// Import your newly created Sidebar.vue component
import Sidebar from './views/Sidebar.vue'

const router = useRouter()
const route = useRoute()
const cartStore = useCartStore()

const searchQuery = ref('')
const isSidebarOpen = ref(false)
const isCurrencyOpen = ref(false)

// Close mobile layout menus automatically when navigating paths
watch(() => route.path, () => {
  isSidebarOpen.value = false
  isCurrencyOpen.value = false
})

const performSearch = () => {
  if (!searchQuery.value || searchQuery.value.trim() === '') return
  router.push({ path: '/search', query: { q: searchQuery.value.trim() } })
}

const setCurrency = (curr) => {
  cartStore.setCurrency(curr)
  isCurrencyOpen.value = false
}

onMounted(() => {
  // Closes open popups gracefully on outside view space mouse clicks
  window.addEventListener('click', () => {
    isCurrencyOpen.value = false
  })
})
</script>