<template>
  <div class="min-h-screen flex flex-col font-brand text-gray-900 bg-white">
    <!-- Header Block -->
    <header class="sticky top-0 z-50 bg-purple-500/10 backdrop-blur-md border-b border-purple-500/20 shadow-lg shadow-purple-500/5">
      <!-- Scrolling admin ticker: Admin → Store settings → Top scrolling messages.
           One message per line, loops seamlessly; hidden when disabled or empty. -->
      <div v-if="site.tickerEnabled && site.tickerMessages.length" class="bg-gradient-brand text-white overflow-hidden" role="marquee" aria-label="Store announcements">
        <div
          class="ticker-track flex items-center whitespace-nowrap py-0 h-8 will-change-transform"
          :style="{ animationDuration: `${site.tickerSpeed}s` }"
        >
          <span v-for="(msg, i) in [...site.tickerMessages, ...site.tickerMessages]" :key="i" class="mx-8 text-[11px] font-medium tracking-wide inline-flex items-center gap-8">
            {{ msg }} <span aria-hidden="true">✦</span>
          </span>
        </div>
      </div>
      <div class="max-w-[1600px] mx-auto px-4 sm:px-6 flex items-center justify-between gap-3 md:gap-8 h-16">
        <!-- Brand: logo + store name + tagline, all from Admin → Site settings -->
        <div class="flex items-center gap-1.5 sm:gap-2 min-w-0">
          <BrandLogo />
        </div>

        <!-- Central Search Context -->
        <div class="flex-1 max-w-xl min-w-0">
          <div class="group relative w-full">
            <span class="absolute inset-y-0 left-0 flex items-center pl-4 text-gray-400 group-focus-within:text-brand-accent transition-colors">
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-4.35-4.35M17 11a6 6 0 11-12 0 6 6 0 0112 0z"></path>
              </svg>
            </span>
          <input 
            v-model="searchQuery" 
            @keyup.enter="performSearch" 
            placeholder="Search for products..." 
            class="w-full bg-gray-50 border border-gray-200 rounded-full py-2.5 pl-11 pr-4 text-sm outline-none focus:border-brand-accent focus:bg-white focus:ring-4 focus:ring-brand-accent/10 transition"
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
          <router-link to="/cart" class="relative p-2 sm:p-2.5 bg-white rounded-full transition-all duration-200 hover:scale-105 hover:shadow-lg hover:shadow-slate-900/20" aria-label="View cart">
            <svg class="w-6 h-6 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path d="M6 2L3 6v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V6l-3-4Z" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"></path>
              <path d="M3 6h18" stroke-width="2" stroke-linecap="round"></path>
              <path d="M16 10a4 4 0 0 1-8 0" stroke-width="2" stroke-linecap="round"></path>
            </svg>
            <span v-if="cartStore.cartTotalLength > 0" class="absolute -top-0.5 -right-0.5 bg-gradient-brand text-white text-[10px] min-w-[18px] h-[18px] px-1 flex items-center justify-center rounded-full font-bold ring-2 ring-white">
              {{ cartStore.cartTotalLength }}
            </span>
          </router-link>

          <!-- Wishlist -->
          <router-link
            to="/wishlist"
            class="relative p-2 sm:p-2.5 bg-white rounded-full transition-all duration-200 hover:scale-105 hover:shadow-lg hover:shadow-slate-900/20" aria-label="Wishlist"
          >
            <span class="text-xl text-purple-600">❤️</span>
            <span v-if="wishlistStore.count" class="absolute -top-0.5 -right-0.5 bg-gradient-brand text-white text-[10px] min-w-[18px] h-[18px] px-1 flex items-center justify-center rounded-full font-bold ring-2 ring-white">
              {{ wishlistStore.count }}
            </span>
          </router-link>

          <!-- Account menu -->
          <div class="relative" @click.stop="isAccountOpen = !isAccountOpen">
            <button class="flex items-center gap-1.5 p-2 sm:pl-2 sm:pr-3 bg-white rounded-full transition-all duration-200 hover:scale-105 hover:shadow-lg hover:shadow-slate-900/20 font-semibold" aria-label="Account menu">
              <svg class="w-6 h-6 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
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
      <!-- Aarong-style category row under navbar (replaces sidebar) -->
      <CategoryNav />
    </header>

    <!-- Full-width content (no sidebar gutter) -->
    <div class="flex-1 w-full max-w-[1600px] mx-auto">
      <!-- Main Display Route Target Space Slot -->
      <main class="w-full px-4 sm:px-6 py-6 min-w-0 bg-white">
        <router-view />
      </main>
    </div>

    <!-- Footer: 3D purple glass — transparent purple shading with depth -->
    <footer class="bg-slate-950 text-slate-300 px-4 sm:px-6 pt-10 pb-6 font-brand text-sm">
      <div class="max-w-7xl mx-auto grid grid-cols-2 md:grid-cols-4 lg:grid-cols-5 gap-8 pb-8 border-b border-white/10">
        <div class="col-span-2 lg:col-span-2">
          <BrandLogo size="sm" />
          <!-- About line: Admin → Site settings → Brand & header → Footer about -->
          <p class="text-slate-400 text-[13px] leading-relaxed mt-3 max-w-xs">{{ site.footerAbout }}</p>
          <!-- Newsletter (shown only when Admin → Customer notification settings allow it) -->
          <form v-if="site.newsletterSignupEnabled" @submit.prevent="subscribeNewsletter" class="mt-4 max-w-xs">
            <label class="text-[11px] font-extrabold uppercase tracking-[0.2em] text-slate-400">Get 10% off your first order</label>
            <div class="flex gap-2 mt-2">
              <input
                v-model="newsletterEmail"
                type="email" required placeholder="Email address"
                class="flex-1 min-w-0 bg-white/10 border border-white/15 rounded-full px-4 py-2.5 text-white placeholder:text-slate-500 outline-none focus:border-brand-accent focus:ring-2 focus:ring-brand-accent/30 transition"
              />
              <button class="shrink-0 bg-gradient-brand text-white text-xs font-extrabold uppercase tracking-wider px-4 py-2.5 rounded-full hover:brightness-110 transition active:scale-95">
                {{ newsletterDone ? '✓ Joined' : 'Join' }}
              </button>
            </div>
            <p v-if="newsletterDone" class="text-emerald-400 text-xs font-semibold mt-2">You're on the list — welcome!</p>
            <p v-else-if="newsletterError" class="text-rose-400 text-xs font-semibold mt-2">{{ newsletterError }}</p>
          </form>
        </div>
        <nav aria-label="Shop">
          <p class="text-[11px] font-extrabold uppercase tracking-[0.2em] text-slate-500 mb-3">Shop</p>
          <ul class="space-y-2 font-medium">
            <li><router-link to="/" class="hover:text-white transition">All products</router-link></li>
            <li><router-link to="/new-arrivals" class="hover:text-white transition">New arrivals</router-link></li>
            <li><router-link to="/cart" class="hover:text-white transition">Shopping bag</router-link></li>
            <li><router-link to="/order-history" class="hover:text-white transition">Track order</router-link></li>
          </ul>
        </nav>
        <nav aria-label="Support">
          <p class="text-[11px] font-extrabold uppercase tracking-[0.2em] text-slate-500 mb-3">Support</p>
          <ul class="space-y-2 font-medium">
            <li v-for="legal in LEGAL_LINKS" :key="legal.hash">
              <router-link :to="`/legal#${legal.hash}`" class="hover:text-white transition">{{ legal.label }}</router-link>
            </li>
            <li v-if="brand.supportEmail"><a :href="`mailto:${brand.supportEmail}`" class="hover:text-white transition">{{ brand.supportEmail }}</a></li>
            <li class="text-slate-500 text-xs pt-1">{{ site.storeName }} · {{ brand.domain }}</li>
          </ul>
        </nav>
        <div>
          <p class="text-[11px] font-extrabold uppercase tracking-[0.2em] text-slate-500 mb-3">Follow</p>
          <div class="flex flex-wrap gap-2">
            <!-- Social links — styled like header cart/wishlist/account icons -->
            <a v-for="link in site.socialLinks" :key="link.key" :href="link.url" target="_blank" rel="noopener" :title="link.label" class="w-9 h-9 rounded-full bg-white/10 hover:bg-white/25 flex items-center justify-center transition"><SocialIcon :name="link.key" class="w-4 h-4 text-white" /></a>
            <a v-if="site.whatsappEnabled" :href="site.whatsappBaseLink" target="_blank" rel="noopener" title="WhatsApp Chat" class="w-9 h-9 rounded-full bg-white/10 hover:bg-white/25 flex items-center justify-center transition"><SocialIcon name="whatsapp" class="w-4 h-4 text-white" /></a>
          </div>
          <p class="text-slate-500 text-xs mt-4 leading-relaxed">Secure checkout<br/><span v-if="site.stripeEnabled">Stripe</span><span v-if="site.stripeEnabled && (site.paypalEnabled || site.whatsappEnabled)"> · </span><span v-if="site.paypalEnabled">PayPal</span><span v-if="site.paypalEnabled && site.whatsappEnabled"> · </span><span v-if="site.whatsappEnabled">WhatsApp</span><span v-if="!site.stripeEnabled && !site.paypalEnabled && !site.whatsappEnabled">Contact us to order</span></p>
        </div>
      </div>
      <div class="max-w-7xl mx-auto pt-5 flex flex-col sm:flex-row items-center justify-between gap-2 text-xs text-slate-500">
        <span class="font-semibold">© {{ new Date().getFullYear() }} {{ site.storeName }} · All rights reserved</span>
        <span class="text-slate-500">{{ site.footerBottomNote }}</span>
      </div>
    </footer>

    <!-- Floating WhatsApp / Facebook quick actions -->
    <SocialButtons />

    <!-- AI chat assistant -->
    <ChatbotWidget />
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import axios from 'axios'
import { useRouter, useRoute } from 'vue-router'
import { useCartStore, CURRENCIES } from './stores/cart'
import { useAuthStore } from './stores/auth'
import { useSiteStore } from './stores/site'
import { useWishlistStore } from './stores/wishlist'
// Top category nav (Aarong-style) replaces the old left sidebar
import CategoryNav from './components/CategoryNav.vue'
import SocialButtons from './components/SocialButtons.vue'
import SocialIcon from './components/SocialIcon.vue'
import BrandLogo from './components/BrandLogo.vue'
import ChatbotWidget from './components/ChatbotWidget.vue'
import { BRAND_CONFIG } from './brand.config'

const router = useRouter()
const route = useRoute()
const cartStore = useCartStore()
const auth = useAuthStore()
const site = useSiteStore()
const wishlistStore = useWishlistStore()
const brand = BRAND_CONFIG
const currencies = CURRENCIES

// Footer links into the dedicated /legal page (opens the matching tab).
const LEGAL_LINKS = [
  { label: 'Terms & Conditions', hash: 'legal-terms' },
  { label: 'Privacy', hash: 'legal-privacy' },
  { label: 'Licence', hash: 'legal-licence' },
]

const FLAGS = { PT: '🇵🇹', PK: '🇵🇰', US: '🇺🇸', SE: '🇸🇪', BD: '🇧🇩' }
const activeRegion = computed(() => CURRENCIES.find((c) => c.code === cartStore.currentCurrency) || CURRENCIES[0])
const countryCode = computed(() => activeRegion.value.country)
const countryFlag = computed(() => FLAGS[activeRegion.value.country] || '🌍')

const searchQuery = ref('')
const isCurrencyOpen = ref(false)
const isAccountOpen = ref(false)
const newsletterEmail = ref('')
const newsletterDone = ref(false)
const newsletterError = ref('')

// Hand the address to the backend (POST /api/v1/newsletter/subscribe/), which
// re-checks the admin consent row and forwards it to the shop mailbox. The old
// localStorage-only version never reached the shop — it only claimed it did.
const subscribeNewsletter = async () => {
  if (!newsletterEmail.value || !newsletterEmail.value.includes('@')) return
  newsletterError.value = ''
  try {
    await axios.post('/api/v1/newsletter/subscribe/', { email: newsletterEmail.value })
    newsletterDone.value = true
    newsletterEmail.value = ''
  } catch (err) {
    newsletterError.value = err.response?.data?.error ||
      'Could not sign you up right now. Please try again later.'
  }
}

// Close mobile layout menus automatically when navigating paths
watch(() => route.path, () => {
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
  // Hydrate wishlist from the server when signed in
  if (localStorage.getItem('token')) await wishlistStore.hydrate()
  // Closes open popups gracefully on outside view space mouse clicks
  window.addEventListener('click', () => {
    isCurrencyOpen.value = false
    isAccountOpen.value = false
  })
})

// Hydrate wishlist whenever the user logs in mid-session (token appears).
watch(
  () => localStorage.getItem('token'),
  async (token) => {
    if (token) await wishlistStore.hydrate()
    else wishlistStore.clear()
  }
)
</script>