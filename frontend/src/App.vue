<template>
  <div class="min-h-screen flex flex-col font-brand text-gray-900 bg-white">
    <!-- Header Block -->
    <header ref="headerRef" class="sticky top-0 z-50 bg-white border-b border-black/10">
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
      <div class="relative mx-auto flex h-14 max-w-[1600px] items-center justify-between px-2 sm:h-16 sm:px-6 md:h-[72px]">
        <div class="flex min-w-0 items-center gap-1 sm:gap-2">
          <button
            @click.stop="toggleCategoryMenu"
            @mouseenter="openCategoryMenu"
            @mouseleave="scheduleCategoryMenuClose"
            class="flex h-8 w-8 shrink-0 items-center justify-center border border-black/15 text-black transition-colors hover:bg-black hover:text-white sm:h-10 sm:w-10"
            :aria-expanded="isCatMenuOpen"
            aria-label="Open category menu"
            aria-controls="category-menu"
          >
              <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h16"></path>
              </svg>
          </button>
          <router-link
            to="/search"
            class="flex h-8 w-8 shrink-0 items-center justify-center border border-transparent transition-colors hover:border-black/15 sm:h-10 sm:w-10"
            aria-label="Search products"
          >
            <svg class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.7" d="m21 21-4.35-4.35M17 10.5a6.5 6.5 0 1 1-13 0 6.5 6.5 0 0 1 13 0Z"></path>
            </svg>
          </router-link>

          <div class="relative shrink-0 select-none">
            <button
              @click.stop="isCurrencyOpen = !isCurrencyOpen"
              class="flex h-8 items-center gap-0.5 border border-transparent px-1 transition-colors hover:border-black/15 sm:h-10 sm:gap-1 sm:px-2"
              :aria-label="`Change currency, currently ${cartStore.currentCurrency}`"
              :aria-expanded="isCurrencyOpen"
            >
              <span class="text-xs leading-none sm:text-sm">{{ countryFlag }}</span>
              <span class="text-[9px] font-semibold sm:text-[11px]">{{ cartStore.currentCurrency }}</span>
              <svg class="hidden h-3 w-3 text-gray-500 sm:block" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="m6 9 6 6 6-6"></path>
              </svg>
            </button>
            <div v-if="isCurrencyOpen" class="absolute left-0 mt-2 z-50 w-40 border border-black/15 bg-white py-1 shadow-xl">
              <p class="border-b border-black/10 px-3 py-1.5 text-[10px] font-semibold uppercase tracking-wider text-gray-500">Currency</p>
              <button
                v-for="c in currencies"
                :key="c.code"
                @click.stop="setCurrency(c.code)"
                class="flex w-full items-center justify-between px-3 py-2 text-left text-sm transition-colors hover:bg-gray-100"
              >
                <span>{{ currencyFlag(c) }} {{ c.code }} ({{ c.symbol }})</span>
                <span v-if="c.code === cartStore.currentCurrency" class="font-bold">✓</span>
              </button>
            </div>
          </div>
        </div>

        <router-link to="/" aria-label="Maims — go to homepage" class="absolute left-1/2 flex -translate-x-1/2 items-center justify-center">
          <img
            v-if="site.logoUrl"
            :src="site.logoUrl"
            :alt="site.storeName + ' logo'"
            class="block h-12 w-[min(7rem,calc(100vw-220px))] object-contain sm:h-14 sm:w-auto sm:max-w-[15rem] md:h-16 md:max-w-[18rem]"
          />
          <svg v-else class="block h-11 w-11 sm:h-12 sm:w-12 md:h-14 md:w-14" viewBox="0 0 40 40" fill="none" aria-hidden="true">
            <defs>
              <linearGradient id="maimsLogoGradMobile" x1="0" y1="0" x2="1" y2="1">
                <stop offset="0" stop-color="#111111" />
                <stop offset="1" stop-color="#555555" />
              </linearGradient>
            </defs>
            <rect width="40" height="40" fill="url(#maimsLogoGradMobile)" />
            <path d="M13 27.5V12.5L20 22.5L27 12.5V27.5" stroke="#FFFFFF" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round" />
          </svg>
        </router-link>
        <div class="flex shrink-0 items-center justify-end gap-0 sm:gap-2">
          <router-link to="/wishlist" class="relative flex h-7 w-7 items-center justify-center sm:h-10 sm:w-10 border border-transparent hover:border-black/15 transition-colors" aria-label="Wishlist">
            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.7" d="M20.8 8.8c0 5.2-8.8 10.1-8.8 10.1S3.2 14 3.2 8.8A4.3 4.3 0 0 1 12 6.9a4.3 4.3 0 0 1 8.8 1.9Z"></path>
            </svg>
            <span v-if="wishlistStore.count" class="absolute -top-0.5 -right-0.5 bg-black text-white text-[9px] min-w-4 h-4 px-1 flex items-center justify-center font-semibold">
              {{ wishlistStore.count }}
            </span>
          </router-link>

          <router-link to="/cart" class="relative flex h-7 w-7 items-center justify-center sm:h-10 sm:w-10 border border-transparent hover:border-black/15 transition-colors" aria-label="View cart">
            <svg class="w-5 h-5 md:w-6 md:h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path d="M6 2L3 6v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V6l-3-4Z" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"></path>
              <path d="M3 6h18" stroke-width="2" stroke-linecap="round"></path>
              <path d="M16 10a4 4 0 0 1-8 0" stroke-width="2" stroke-linecap="round"></path>
            </svg>
            <span v-if="cartStore.cartTotalLength > 0" class="absolute -top-0.5 -right-0.5 bg-black text-white text-[9px] min-w-4 h-4 px-1 flex items-center justify-center font-semibold">
              {{ cartStore.cartTotalLength }}
            </span>
          </router-link>

          <!-- Account menu -->
          <div class="relative">
            <button @click.stop="isAccountOpen = !isAccountOpen" class="flex h-7 w-7 items-center justify-center sm:h-10 sm:w-10 border border-transparent hover:border-black/15 transition-colors" aria-label="Account menu" :aria-expanded="isAccountOpen">
              <svg class="w-5 h-5 md:w-6 md:h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"></path>
              </svg>
            </button>
            <div v-if="isAccountOpen" class="absolute right-0 mt-2 bg-white border border-black/15 shadow-xl w-48 z-50 py-1.5 overflow-hidden">
              <template v-if="auth.isAuthenticated">
                <p class="px-4 py-2 text-xs text-gray-400 font-bold uppercase tracking-wider border-b border-gray-50">Hi, {{ auth.username }}</p>
                  <router-link to="/profile" class="block px-4 py-2 hover:bg-gray-100 text-sm">Profile</router-link>
                  <router-link to="/order-history" class="block px-4 py-2 hover:bg-gray-100 text-sm">Orders</router-link>
                <button @click.stop="logout" class="block w-full text-left px-4 py-2 hover:bg-gray-50 text-sm text-red-600 font-semibold">Log Out</button>
              </template>
              <template v-else>
                <router-link to="/log-in" class="block px-4 py-2 hover:bg-gray-100 text-sm font-semibold">Log In</router-link>
                <router-link to="/sign-up" class="block px-4 py-2 hover:bg-gray-100 text-sm">Sign Up</router-link>
              </template>
            </div>
          </div>
        </div>
      </div>
    </header>

    <div
      v-if="isCatMenuOpen"
      class="fixed inset-x-0 bottom-0 z-[60] bg-black/30"
      :style="{ top: `${headerHeight}px` }"
      @click.self="closeCategoryMenu"
      @mouseenter="clearCategoryMenuClose"
      @mouseleave="scheduleCategoryMenuClose"
    >
      <aside id="category-menu" class="h-full w-full max-w-md overflow-y-auto border-r border-black/15 bg-white px-5 py-5 sm:px-8" aria-label="Shop categories">
        <div class="flex items-center justify-between border-b border-black/10 pb-3">
          <h2 class="font-semibold uppercase tracking-[0.16em] text-sm">Shop</h2>
          <button class="flex h-9 w-9 items-center justify-center border border-black/15 text-xl" @click="closeCategoryMenu" aria-label="Close category menu">×</button>
        </div>
        <nav class="py-3">
          <router-link to="/" class="block border-b border-black/10 py-3 text-sm font-medium" @click="closeCategoryMenu">All Products</router-link>
          <router-link to="/new-arrivals" class="block border-b border-black/10 py-3 text-sm font-medium" @click="closeCategoryMenu">New Arrivals</router-link>
          <div v-for="category in navCats" :key="category.slug" class="border-b border-black/10">
            <div class="flex items-center justify-between gap-3 py-3">
              <router-link :to="`/category/${category.slug}`" class="text-sm font-semibold uppercase tracking-wide" @click="closeCategoryMenu">{{ category.name }}</router-link>
              <button
                v-if="category.children?.length"
                @click="toggleSubcategory(category.slug)"
                class="flex h-8 w-8 items-center justify-center border border-black/15 text-lg"
                :aria-expanded="expandedCategory === category.slug"
                :aria-label="`${expandedCategory === category.slug ? 'Hide' : 'Show'} ${category.name} subcategories`"
              >{{ expandedCategory === category.slug ? '−' : '+' }}</button>
            </div>
            <div v-if="category.children?.length && expandedCategory === category.slug" class="grid grid-cols-2 gap-x-3 border-t border-black/10 py-2">
              <router-link
                v-for="subcategory in category.children"
                :key="subcategory.slug"
                :to="`/category/${subcategory.slug}`"
                class="py-2 text-sm text-gray-600 hover:text-black"
                @click="closeCategoryMenu"
              >{{ subcategory.name }}</router-link>
            </div>
          </div>
        </nav>
        <div class="mt-3 border-t border-black/15 pt-4">
          <p class="mb-2 text-[10px] font-semibold uppercase tracking-[0.18em] text-gray-500">Account</p>
          <template v-if="auth.isAuthenticated">
            <p class="mb-2 text-sm">Signed in as {{ auth.username }}</p>
            <router-link to="/profile" class="block py-2 text-sm" @click="closeCategoryMenu">Profile</router-link>
            <router-link to="/order-history" class="block py-2 text-sm" @click="closeCategoryMenu">Orders</router-link>
            <button @click="logout" class="py-2 text-sm font-medium underline">Log Out</button>
          </template>
          <template v-else>
            <router-link to="/log-in" class="mr-5 py-2 text-sm font-medium underline" @click="closeCategoryMenu">Log In</router-link>
            <router-link to="/sign-up" class="py-2 text-sm underline" @click="closeCategoryMenu">Sign Up</router-link>
          </template>
        </div>
      </aside>
    </div>

    <!-- Full-width content (no sidebar gutter) -->
    <div class="flex-1 w-full max-w-[1600px] mx-auto">
      <!-- Main Display Route Target Space Slot -->
      <main class="w-full min-w-0 bg-white" :class="route.path === '/' ? '' : 'px-4 sm:px-6 py-6'">
        <router-view />
      </main>
    </div>

    <!-- Footer -->
    <footer class="site-footer bg-black text-slate-200 px-4 sm:px-6 pt-10 pb-6 font-brand text-sm">
      <div class="max-w-7xl mx-auto grid grid-cols-2 md:grid-cols-4 lg:grid-cols-5 gap-8 pb-8 border-b border-white/10">
        <div class="col-span-2 lg:col-span-2">
          <BrandLogo size="sm" />
          <!-- About line: Admin → Site settings → Brand & header → Footer about -->
          <p class="text-slate-200 text-[13px] leading-relaxed mt-3 max-w-xs">{{ site.footerAbout }}</p>
          <!-- Newsletter (shown only when Admin → Customer notification settings allow it) -->
          <form v-if="site.newsletterSignupEnabled" @submit.prevent="subscribeNewsletter" class="mt-4 max-w-xs">
            <label class="text-[11px] font-extrabold uppercase tracking-[0.2em] text-slate-200">Get 10% off your first order</label>
            <div class="flex gap-2 mt-2">
              <input
                v-model="newsletterEmail"
                type="email" required placeholder="Email address"
                class="flex-1 min-w-0 bg-white/10 border border-white/30 rounded-full px-4 py-2.5 text-white placeholder:text-slate-300 outline-none focus:border-white focus:ring-2 focus:ring-white/30 transition"
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
          <p class="text-[11px] font-extrabold uppercase tracking-[0.2em] text-slate-300 mb-3">Shop</p>
          <ul class="space-y-2 font-medium">
            <li><router-link to="/" class="hover:text-white transition">All products</router-link></li>
            <li><router-link to="/new-arrivals" class="hover:text-white transition">New arrivals</router-link></li>
            <li><router-link to="/cart" class="hover:text-white transition">Shopping bag</router-link></li>
            <li><router-link to="/order-history" class="hover:text-white transition">Track order</router-link></li>
          </ul>
        </nav>
        <nav aria-label="Support">
          <p class="text-[11px] font-extrabold uppercase tracking-[0.2em] text-slate-300 mb-3">Support</p>
          <ul class="space-y-2 font-medium">
            <li v-for="legal in LEGAL_LINKS" :key="legal.hash">
              <router-link :to="`/legal#${legal.hash}`" class="hover:text-white transition">{{ legal.label }}</router-link>
            </li>
            <li v-if="brand.supportEmail"><a :href="`mailto:${brand.supportEmail}`" class="hover:text-white transition">{{ brand.supportEmail }}</a></li>
            <li class="text-slate-300 text-xs pt-1">{{ site.storeName }} · {{ brand.domain }}</li>
          </ul>
        </nav>
        <div>
          <p class="text-[11px] font-extrabold uppercase tracking-[0.2em] text-slate-300 mb-3">Follow</p>
          <div class="flex flex-wrap gap-2">
            <!-- Social links — styled like header cart/wishlist/account icons -->
            <a v-for="link in site.socialLinks" :key="link.key" :href="link.url" target="_blank" rel="noopener" :title="link.label" class="w-9 h-9 rounded-full bg-white/10 hover:bg-white/25 flex items-center justify-center transition"><SocialIcon :name="link.key" class="w-4 h-4 text-white" /></a>
            <a v-if="site.whatsappEnabled" :href="site.whatsappBaseLink" target="_blank" rel="noopener" title="WhatsApp Chat" class="w-9 h-9 rounded-full bg-white/10 hover:bg-white/25 flex items-center justify-center transition"><SocialIcon name="whatsapp" class="w-4 h-4 text-white" /></a>
          </div>
          <p class="text-slate-300 text-xs mt-4 leading-relaxed">Secure checkout<br/><span v-if="site.stripeEnabled">Stripe</span><span v-if="site.stripeEnabled && (site.paypalEnabled || site.whatsappEnabled)"> · </span><span v-if="site.paypalEnabled">PayPal</span><span v-if="site.paypalEnabled && site.whatsappEnabled"> · </span><span v-if="site.whatsappEnabled">WhatsApp</span><span v-if="!site.stripeEnabled && !site.paypalEnabled && !site.whatsappEnabled">Contact us to order</span></p>
        </div>
      </div>
      <div class="max-w-7xl mx-auto pt-5 flex flex-col sm:flex-row items-center justify-between gap-2 text-xs text-slate-300">
        <span class="font-semibold">© {{ new Date().getFullYear() }} {{ site.storeName }} · All rights reserved</span>
        <span class="text-slate-300">{{ site.footerBottomNote }}</span>
      </div>
    </footer>

    <!-- AI chat assistant -->
    <ChatbotWidget />
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount, watch } from 'vue'
import axios from 'axios'
import { useRouter, useRoute } from 'vue-router'
import { useCartStore, CURRENCIES } from './stores/cart'
import { useAuthStore } from './stores/auth'
import { useSiteStore } from './stores/site'
import { useWishlistStore } from './stores/wishlist'
import BrandLogo from './components/BrandLogo.vue'
import SocialIcon from './components/SocialIcon.vue'
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

const FLAGS = { EU: '🇪🇺', PT: '🇪🇺', PK: '🇵🇰', US: '🇺🇸', SE: '🇸🇪', BD: '🇧🇩' }
const activeRegion = computed(() => CURRENCIES.find((c) => c.code === cartStore.currentCurrency) || CURRENCIES[0])
const countryFlag = computed(() => FLAGS[activeRegion.value.country] || '🌍')

const isCurrencyOpen = ref(false)
const isAccountOpen = ref(false)
const isCatMenuOpen = ref(false)
const expandedCategory = ref('')
const navCats = ref([])
const headerRef = ref(null)
const headerHeight = ref(0)
const newsletterEmail = ref('')
const newsletterDone = ref(false)
const newsletterError = ref('')
let categoryMenuCloseTimer = null
let headerResizeObserver = null

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

const currencyFlag = (currency) => FLAGS[currency.country] || '🌍'
const clearCategoryMenuClose = () => clearTimeout(categoryMenuCloseTimer)
const openCategoryMenu = () => {
  clearCategoryMenuClose()
  isCatMenuOpen.value = true
}
const scheduleCategoryMenuClose = () => {
  clearCategoryMenuClose()
  categoryMenuCloseTimer = setTimeout(() => {
    isCatMenuOpen.value = false
  }, 250)
}
const closeCategoryMenu = () => {
  clearCategoryMenuClose()
  isCatMenuOpen.value = false
}
const toggleCategoryMenu = () => {
  if (isCatMenuOpen.value) closeCategoryMenu()
  else openCategoryMenu()
}
const toggleSubcategory = (slug) => {
  expandedCategory.value = expandedCategory.value === slug ? '' : slug
}
const updateHeaderHeight = () => {
  headerHeight.value = headerRef.value?.getBoundingClientRect().bottom || 0
}
const onDocumentClick = (event) => {
  if (!headerRef.value?.contains(event.target)) {
    isCurrencyOpen.value = false
    isAccountOpen.value = false
  }
}
const onKeydown = (event) => {
  if (event.key === 'Escape') {
    isCurrencyOpen.value = false
    isAccountOpen.value = false
    closeCategoryMenu()
  }
}

// Close menus automatically when navigating paths
watch(() => route.path, () => {
  isCurrencyOpen.value = false
  isAccountOpen.value = false
  closeCategoryMenu()
})

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
  // Hamburger category menu items
  try {
    const res = await axios.get('/api/v1/categories/')
    navCats.value = Array.isArray(res.data) ? res.data : []
  } catch (error) {
    console.error('Category menu could not load:', error)
  }
  updateHeaderHeight()
  if (headerRef.value && typeof ResizeObserver !== 'undefined') {
    headerResizeObserver = new ResizeObserver(updateHeaderHeight)
    headerResizeObserver.observe(headerRef.value)
  }
  window.addEventListener('resize', updateHeaderHeight)
  document.addEventListener('click', onDocumentClick)
  document.addEventListener('keydown', onKeydown)
})

onBeforeUnmount(() => {
  clearCategoryMenuClose()
  headerResizeObserver?.disconnect()
  window.removeEventListener('resize', updateHeaderHeight)
  document.removeEventListener('click', onDocumentClick)
  document.removeEventListener('keydown', onKeydown)
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