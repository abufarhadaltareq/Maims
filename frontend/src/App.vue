<template>
  <div class="min-h-screen flex flex-col font-brand text-gray-900 bg-white">
    <!-- Header Block -->
    <header class="sticky top-0 z-50 bg-white/90 backdrop-blur-md border-b border-gray-100">
      <div v-if="brand.announcement" class="bg-[#0F0F12] text-white">
        <div class="max-w-[1600px] mx-auto px-4 sm:px-6 h-8 flex items-center justify-center">
          <p class="text-[11px] font-medium tracking-wide text-center truncate">{{ brand.announcement }}</p>
        </div>
      </div>
      <div class="max-w-[1600px] mx-auto px-4 sm:px-6 flex items-center justify-between gap-3 md:gap-8 h-16">
        
        <div class="flex items-center gap-1.5 sm:gap-2 min-w-0">
          <!-- Mobile Sidebar Toggle button -->
          <button
            @click="isSidebarOpen = !isSidebarOpen"
            class="lg:hidden -ml-1 p-2 text-gray-600 hover:bg-gray-100 hover:text-black rounded-full transition-colors"
            aria-label="Toggle menu"
          >
            <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h16"></path>
            </svg>
          </button>
          <BrandLogo />
        </div>

        <!-- Central Search Context -->
        <div class="flex-1 max-w-xl min-w-0">
          <div class="group relative w-full">
            <span class="absolute inset-y-0 left-0 flex items-center pl-4 text-gray-400 group-focus-within:text-black transition-colors">
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-4.35-4.35M17 11a6 6 0 11-12 0 6 6 0 0112 0z"></path>
              </svg>
            </span>
          <input 
            v-model="searchQuery" 
            @keyup.enter="performSearch" 
            placeholder="Search for products..." 
            class="w-full bg-gray-50 border border-gray-200 rounded-full py-2.5 pl-11 pr-4 text-sm outline-none focus:border-black focus:bg-white focus:ring-4 focus:ring-black/5 transition"
          >
          </div>
        </div>
        
        <!-- Right Utility Actions -->
        <div class="flex items-center gap-0.5 sm:gap-1.5">
          <!-- Currency Picker -->
          <div class="relative select-none" @click.stop="isCurrencyOpen = !isCurrencyOpen">
            <button class="flex items-center gap-1.5 sm:gap-2 px-2 sm:px-3 py-2 rounded-full hover:bg-gray-100 transition-colors" aria-label="Change currency">
              <span class="text-lg leading-none">{{ countryFlag }}</span>
              <span class="hidden sm:flex flex-col items-start leading-tight">
                <span class="text-[9px] text-gray-400 font-bold uppercase tracking-wider">Deliver to</span>
                <span class="text-xs font-semibold text-gray-800">{{ countryCode }} · {{ cartStore.currentCurrency }}</span>
              </span>
              <svg class="hidden sm:block w-3 h-3 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M19 9l-7 7-7-7"></path>
              </svg>
            </button>

            <div v-if="isCurrencyOpen" class="absolute right-0 mt-2 bg-white border border-gray-100 shadow-xl rounded-2xl w-40 z-50 py-1.5 overflow-hidden">
              <p class="px-4 py-1.5 text-[10px] font-bold uppercase tracking-wider text-gray-400 border-b border-gray-50">Currency</p>
              <button
                v-for="c in currencies"
                :key="c.code"
                @click.stop="setCurrency(c.code)"
                class="w-full text-left px-4 py-2 hover:bg-gray-50 text-sm transition-colors flex items-center justify-between"
              >
                <span>{{ c.code }} ({{ c.symbol }})</span>
                <span v-if="c.code === cartStore.currentCurrency" class="text-emerald-600 font-black">✓</span>
              </button>
            </div>
          </div>

          <!-- Cart -->
          <router-link to="/cart" class="relative p-2 sm:p-2.5 text-gray-700 hover:text-black hover:bg-gray-100 rounded-full transition-colors" aria-label="View cart">
            <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path d="M6 2L3 6v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V6l-3-4Z" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"></path>
              <path d="M3 6h18" stroke-width="2" stroke-linecap="round"></path>
              <path d="M16 10a4 4 0 0 1-8 0" stroke-width="2" stroke-linecap="round"></path>
            </svg>
            <span v-if="cartStore.cartTotalLength > 0" class="absolute -top-0.5 -right-0.5 bg-[#0F0F12] text-white text-[10px] min-w-[18px] h-[18px] px-1 flex items-center justify-center rounded-full font-bold ring-2 ring-white">
              {{ cartStore.cartTotalLength }}
            </span>
          </router-link>

          <!-- Account menu -->
          <div class="relative" @click.stop="isAccountOpen = !isAccountOpen">
            <button class="flex items-center gap-1.5 p-2 sm:pl-2 sm:pr-3 text-gray-700 hover:text-black hover:bg-gray-100 rounded-full transition-colors font-semibold" aria-label="Account menu">
              <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"></path>
              </svg>
              <span v-if="auth.isAuthenticated" class="max-w-[90px] truncate hidden sm:inline text-sm">{{ auth.username }}</span>
            </button>
            <div v-if="isAccountOpen" class="absolute right-0 mt-2 bg-white border border-gray-100 shadow-xl rounded-2xl w-48 z-50 py-1.5 overflow-hidden">
              <template v-if="auth.isAuthenticated">
                <p class="px-4 py-2 text-xs text-gray-400 font-bold uppercase tracking-wider border-b border-gray-50">Hi, {{ auth.username }}</p>
                <router-link to="/profile" class="block px-4 py-2 hover:bg-gray-50 text-sm">Profile</router-link>
                <router-link to="/order-history" class="block px-4 py-2 hover:bg-gray-50 text-sm">Orders</router-link>
                <button @click.stop="logout" class="block w-full text-left px-4 py-2 hover:bg-gray-50 text-sm text-red-600 font-semibold">Log Out</button>
              </template>
              <template v-else>
                <router-link to="/log-in" class="block px-4 py-2 hover:bg-gray-50 text-sm font-semibold">Log In</router-link>
                <router-link to="/sign-up" class="block px-4 py-2 hover:bg-gray-50 text-sm">Sign Up</router-link>
              </template>
            </div>
          </div>
        </div>
      </div>
    </header>

    <!-- Content Workspace Wrapper Frame Layout -->
    <div class="flex flex-1 max-w-[1600px] mx-auto w-full relative">
      
      <!-- Premium LAAM-Inspired Responsive Sidebar -->
      <Sidebar 
        :class="[
          'transition-all duration-300 lg:block flex-shrink-0', 
          isSidebarOpen ? 'fixed inset-y-0 left-0 z-40 w-64 shadow-2xl bg-white border-r border-gray-100 pt-24 lg:pt-0' : 'hidden'
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

    <!-- Footer with admin-driven Facebook / WhatsApp links -->
    <footer class="border-t border-gray-100 bg-gray-50/70 px-6 py-8 font-brand text-sm text-gray-500">
      <div class="max-w-[1600px] mx-auto flex flex-col md:flex-row items-center justify-between gap-5">
        <div class="flex items-center gap-3">
          <BrandLogo size="sm" :show-tagline="false" />
          <span class="font-semibold text-gray-700">© {{ new Date().getFullYear() }} {{ site.settings?.store_name || 'Maims' }}</span>
        </div>

        <nav class="flex flex-wrap items-center gap-x-5 gap-y-2 font-semibold">
          <a
            v-if="site.facebookShopUrl"
            :href="site.facebookShopUrl"
            target="_blank" rel="noopener"
            class="flex items-center gap-1.5 text-[#1877F2] hover:underline"
          >
            <SocialIcon name="facebook" class="w-4 h-4" />
            Facebook Shop
          </a>
          <a
            v-for="link in site.socialLinks"
            :key="link.key"
            :href="link.url"
            target="_blank" rel="noopener"
            class="flex items-center gap-1.5 hover:underline"
            :class="FOOTER_COLORS[link.key] || 'text-gray-600'"
          >
            <SocialIcon :name="link.key" class="w-4 h-4" />
            {{ link.label }}
          </a>
          <a
            v-if="site.whatsappEnabled"
            :href="site.whatsappBaseLink"
            target="_blank" rel="noopener"
            class="flex items-center gap-1.5 text-[#25D366] hover:underline"
          >
            <SocialIcon name="whatsapp" class="w-4 h-4" />
            WhatsApp Chat
          </a>
          <a v-if="brand.supportEmail" :href="`mailto:${brand.supportEmail}`" class="hover:text-black hover:underline">
            {{ brand.supportEmail }}
          </a>
        </nav>
      </div>
    </footer>

    <!-- Floating WhatsApp / Facebook quick actions -->
    <SocialButtons />
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useCartStore, CURRENCIES } from './stores/cart'
import { useAuthStore } from './stores/auth'
import { useSiteStore } from './stores/site'
// Import your newly created Sidebar.vue component
import Sidebar from './views/Sidebar.vue'
import SocialButtons from './components/SocialButtons.vue'
import SocialIcon from './components/SocialIcon.vue'
import BrandLogo from './components/BrandLogo.vue'
import { BRAND_CONFIG } from './brand.config'

const router = useRouter()
const route = useRoute()
const cartStore = useCartStore()
const auth = useAuthStore()
const site = useSiteStore()
const brand = BRAND_CONFIG
const currencies = CURRENCIES

// Text colours for the footer social links.
const FOOTER_COLORS = {
  facebook: 'text-[#1877F2]',
  instagram: 'text-[#E1306C]',
  tiktok: 'text-black',
  twitter: 'text-black',
  youtube: 'text-[#FF0000]',
  linkedin: 'text-[#0A66C2]',
}

const FLAGS = { PT: '🇵🇹', PK: '🇵🇰', US: '🇺🇸', SE: '🇸🇪', BD: '🇧🇩' }
const activeRegion = computed(() => CURRENCIES.find((c) => c.code === cartStore.currentCurrency) || CURRENCIES[0])
const countryCode = computed(() => activeRegion.value.country)
const countryFlag = computed(() => FLAGS[activeRegion.value.country] || '🌍')

const searchQuery = ref('')
const isSidebarOpen = ref(false)
const isCurrencyOpen = ref(false)
const isAccountOpen = ref(false)

// Close mobile layout menus automatically when navigating paths
watch(() => route.path, () => {
  isSidebarOpen.value = false
  isCurrencyOpen.value = false
  isAccountOpen.value = false
})

const performSearch = () => {
  if (!searchQuery.value || searchQuery.value.trim() === '') return
  router.push({ path: '/search', query: { q: searchQuery.value.trim() } })
}

const setCurrency = (curr) => {
  cartStore.setCurrency(curr)
  isCurrencyOpen.value = false
}

const logout = async () => {
  await auth.logout()
  isAccountOpen.value = false
  router.push('/')
}

onMounted(async () => {
  // Rehydrate user from token (page refresh safe)
  if (localStorage.getItem('token')) await auth.fetchMe()
  // Load admin-driven site settings (Facebook / WhatsApp / payment toggles)
  site.fetchSettings()
  // Closes open popups gracefully on outside view space mouse clicks
  window.addEventListener('click', () => {
    isCurrencyOpen.value = false
    isAccountOpen.value = false
  })
})
</script>