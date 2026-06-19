<template>
  <header class="bg-white border-b border-gray-100 sticky top-0 z-50 px-6 py-4">
    <div class="max-w-7xl mx-auto grid grid-cols-3 items-center w-full">
      
      <div class="flex justify-start">
        <button 
          @click="isMenuOpen = true"
          class="p-2 text-gray-700 hover:text-black transition focus:outline-none"
          aria-label="Open Navigation Menu"
        >
          <svg 
            xmlns="http://www.w3.org/2000/svg" 
            fill="none" 
            viewBox="0 0 24 24" 
            stroke-width="2" 
            stroke="currentColor" 
            class="w-6 h-6"
          >
            <path stroke-linecap="round" stroke-linejoin="round" d="M3.75 6.75h16.5M3.75 12h16.5m-16.5 5.25h16.5" />
          </svg>
        </button>
      </div>

      <div class="flex justify-center">
        <router-link to="/" class="block group">
          <img 
            src="./assets/logo.png" 
            alt="Maims Brand Logo" 
            class="h-20 md:h-25 w-auto object-contain transition duration-200 group-hover:opacity-85"
          />
        </router-link>
      </div>

      <div class="flex justify-end">
        <router-link 
          to="/cart" 
          class="relative p-2 text-gray-700 hover:text-black transition flex items-center gap-1.5 group"
          aria-label="Shopping Cart"
        >
          <svg 
            xmlns="http://www.w3.org/2000/svg" 
            fill="none" 
            viewBox="0 0 24 24" 
            stroke-width="2" 
            stroke="currentColor" 
            class="w-6 h-6 transition transform group-hover:scale-105"
          >
            <path stroke-linecap="round" stroke-linejoin="round" d="M15.75 10.5V6a3.75 3.75 0 10-7.5 0v4.5m11.356-1.993l1.263 12c.07.665-.45 1.243-1.119 1.243H4.25a1.125 1.125 0 01-1.12-1.243l1.264-12A1.125 1.125 0 015.513 7.5h12.974c.576 0 1.059.435 1.119 1.007z" />
          </svg>
          <span class="font-semibold text-sm hidden md:inline">Cart</span>

          <span 
            v-if="cartStore.cartTotalLength > 0"
            class="absolute -top-1 -right-1 bg-blue-600 text-white font-extrabold text-[10px] w-5 h-5 flex items-center justify-center rounded-full shadow-sm animate-pulse"
          >
            {{ cartStore.cartTotalLength }}
          </span>
        </router-link>
      </div>

    </div>
  </header>

  <div 
    class="fixed inset-0 z-[100] transition-opacity duration-300"
    :class="isMenuOpen ? 'opacity-100 pointer-events-auto' : 'opacity-0 pointer-events-none'"
  >
    <div @click="isMenuOpen = false" class="absolute inset-0 bg-black/40 backdrop-blur-sm"></div>
    
    <div 
      class="absolute top-0 bottom-0 left-0 w-80 bg-white shadow-2xl p-6 flex flex-col justify-between transition-transform duration-300 ease-out transform"
      :class="isMenuOpen ? 'translate-x-0' : '-translate-x-full'"
    >
      <div>
        <div class="flex justify-between items-center mb-8">
          <span class="font-brand font-black text-lg tracking-wider uppercase">Menu</span>
          <button @click="isMenuOpen = false" class="text-gray-400 hover:text-black p-1">
            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" class="w-6 h-6">
              <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <nav class="flex flex-col items-start gap-5 w-full text-left">
          
          <div v-if="token" class="text-xs font-bold text-gray-400 uppercase tracking-wide mb-2">
            Welcome back, <span class="text-gray-800 font-black">{{ username }}</span>
          </div>

          <router-link @click="isMenuOpen = false" to="/" class="text-gray-800 hover:text-blue-600 font-bold text-lg transition">
            Home
          </router-link>

          <div v-if="categories.length > 0" class="w-full">
            <p class="text-xs uppercase tracking-[0.28em] text-gray-400 mb-2">Shop by category</p>
            <div class="grid gap-2">
              <router-link
                v-for="category in categories"
                :key="category.id"
                @click="isMenuOpen = false"
                :to="`/category/${category.slug}`"
                class="text-gray-800 hover:text-blue-600 font-semibold text-base transition"
              >
                {{ category.name }}
              </router-link>
            </div>
          </div>
          
          <template v-if="token">
            <router-link @click="isMenuOpen = false" to="/order-history" class="text-gray-800 hover:text-blue-600 font-bold text-lg transition">
              Track Orders
            </router-link>

            <router-link @click="isMenuOpen = false" to="/profile" class="w-full text-gray-800 hover:text-blue-600 font-bold text-lg transition">
              👤 My Profile
            </router-link>

            <button 
              @click="logout" 
              class="w-full text-left mt-4 text-xs font-black text-red-500 uppercase tracking-widest pt-4 border-t border-gray-100 hover:text-red-700 transition"
            >
              🚪 Log Out Account
            </button>
          </template>

          <template v-else>
            <router-link @click="isMenuOpen = false" to="/log-in" class="text-gray-800 hover:text-blue-600 font-bold text-lg transition">
              Log In
            </router-link>
          </template>
        </nav>
      </div>

      <div class="text-xs text-gray-400 font-medium text-left">
        © 2026 {{ config.name }} Apparel House. All Rights Reserved.
      </div>
    </div>
  </div>

  <main>
    <router-view />
  </main>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import axios from 'axios'
import { BRAND_CONFIG } from './brand.config.js'
import { useCartStore } from './stores/cart' 

const config = ref(BRAND_CONFIG)
const cartStore = useCartStore()
const isMenuOpen = ref(false)
const categories = ref([])

const token = ref('')
const username = ref('')
const route = useRoute()
const router = useRouter()

const initializeAuth = () => {
  const storedToken = localStorage.getItem('token')
  const storedUsername = localStorage.getItem('username')
  
  if (storedToken) {
    token.value = storedToken
    username.value = storedUsername || 'User'
    axios.defaults.headers.common['Authorization'] = 'Token ' + storedToken
  } else {
    token.value = ''
    username.value = ''
    delete axios.defaults.headers.common['Authorization']
  }
}

const logout = () => {
  localStorage.removeItem('token')
  localStorage.removeItem('username')
  token.value = ''
  username.value = ''
  delete axios.defaults.headers.common['Authorization']
  isMenuOpen.value = false 
  router.push('/')
}

const fetchCategories = async () => {
  try {
    const response = await axios.get('/api/v1/categories/')
    categories.value = response.data || []
  } catch (error) {
    console.warn('Unable to load category navigation.', error)
  }
}

onMounted(() => {
  initializeAuth()
  fetchCategories()
})

watch(route, () => {
  initializeAuth()
})
</script>