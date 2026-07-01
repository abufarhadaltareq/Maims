<template>
  <div class="py-12 px-6 max-w-5xl mx-auto font-brand text-brand-text">
    <h1 class="text-3xl font-extrabold tracking-tight text-left mb-8">Your Shopping Bag</h1>

    <div v-if="cartStore.items.length === 0" class="text-center py-16 border border-dashed border-gray-200 rounded-xl bg-gray-50/50">
      <p class="text-gray-500 font-medium mb-4">Your bag is currently empty.</p>
      <router-link 
        to="/" 
        class="inline-block bg-black text-white font-bold px-6 py-3 rounded hover:bg-gray-800 transition"
      >
        Explore Collections
      </router-link>
    </div>

    <div v-else class="grid grid-cols-1 lg:grid-cols-3 gap-10 items-start">
      
      <div class="lg:col-span-2 space-y-6">
        <div 
          v-for="item in cartStore.items" 
          :key="`${item.product?.id || item.id}-${item.size || 'default'}`" 
          class="flex items-center gap-4 p-4 border border-gray-100 rounded-xl shadow-sm bg-white"
        >
          <div class="w-20 h-24 bg-brand-muted rounded-lg overflow-hidden flex-shrink-0">
            <img 
              :src="item.product?.get_thumbnail || 'https://placehold.co/100x120'" 
              :alt="item.product?.name || 'Product Image'" 
              class="w-full h-full object-cover object-center"
            />
          </div>

          <div class="flex-1 text-left space-y-2">
            <div>
              <h3 class="font-bold text-base leading-tight">{{ item.product?.name }}</h3>
              <p class="text-sm text-gray-500 font-medium">
                {{ getItemDisplayPrice(item).string }} each
              </p>
              <p v-if="item.size" class="text-xs uppercase tracking-[0.2em] text-gray-400">
                Size: {{ item.size }}
              </p>
            </div>
            
            <div class="flex items-center gap-2 pt-2">
              <button 
                @click="cartStore.decrementQuantity(item.product?.id, item.size)"
                class="w-7 h-7 flex items-center justify-center border border-gray-200 rounded-md text-gray-600 hover:bg-gray-50 active:bg-gray-100 transition text-sm font-bold"
              >
                -
              </button>
              <span class="w-8 text-center font-bold text-sm">
                {{ item.item_quantity || item.quantity }}
              </span>
              <button 
                @click="cartStore.incrementQuantity(item.product?.id, item.size)"
                class="w-7 h-7 flex items-center justify-center border border-gray-200 rounded-md text-gray-600 hover:bg-gray-50 active:bg-gray-100 transition text-sm font-bold"
              >
                +
              </button>
            </div>
          </div>

          <div class="text-right pl-2">
            <p class="font-extrabold text-base whitespace-nowrap">
              {{ (getItemDisplayPrice(item).numeric * (item.item_quantity || item.quantity || 0)).toFixed(2) }} {{ cartStore.currentCurrency }}
            </p>
          </div>
        </div>

        <div class="text-left">
          <button 
            @click="cartStore.clearCart" 
            class="text-xs text-red-500 font-semibold underline hover:text-red-700 transition"
          >
            Clear entire shopping bag
          </button>
        </div>
      </div>

      <div class="bg-gray-50/70 border border-gray-100 rounded-xl p-6 space-y-4 text-left">
        <h2 class="font-bold text-lg tracking-tight mb-2">Order Summary</h2>
        
        <div class="flex justify-between text-sm text-gray-600 font-medium">
          <span>Total Items:</span>
          <span>{{ cartStore.cartTotalLength }} items</span>
        </div>

        <div class="flex justify-between text-sm text-gray-600 font-medium">
          <span>Shipping:</span>
          <span class="text-emerald-600 font-semibold">Free</span>
        </div>

        <hr class="border-gray-200" />

        <div class="flex justify-between items-baseline">
          <span class="font-bold text-base">Estimated Total:</span>
          <span class="font-black text-2xl text-blue-600">
            {{ cartTotalDisplayPrice }}
          </span>
        </div>

        <router-link 
          to="/checkout" 
          class="block w-full text-center bg-blue-600 text-white font-bold py-3.5 rounded-lg shadow hover:bg-blue-700 transition duration-200 mt-4"
        >
          Proceed to Checkout
        </router-link>
      </div>

    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useCartStore } from '../stores/cart'

const cartStore = useCartStore()

// Core currency exchange rates index matching your other views
const ratesToUSD = {
  'SEK': 0.095,
  'PKR': 0.0036,
  'EUR': 1.08,
  'BDT': 0.0085,
  'USD': 1.0
}

// 🌟 DYNAMIC CURRENCY CALCULATOR FOR A NESTED CART ITEM PRODUCT
const getItemDisplayPrice = (item) => {
  const selectedCurrency = cartStore.currentCurrency // e.g., 'BDT'
  const product = item.product || {}
  
  // 1. If the nested product has a specific prices array from the database, try to find an exact match
  if (product.prices && Array.isArray(product.prices)) {
    const regionalPrice = product.prices.find(p => p.currency === selectedCurrency)
    if (regionalPrice) {
      return {
        numeric: parseFloat(regionalPrice.price),
        string: `${Number(regionalPrice.price).toFixed(2)} ${selectedCurrency}`
      }
    }
    
    // 2. Fallback: If no exact match exists, convert using the first available currency object from the array
    const backupPriceObj = product.prices[0]
    if (backupPriceObj) {
      const basePrice = Number(backupPriceObj.price)
      const baseCurrency = backupPriceObj.currency
      
      const rateInUSD = ratesToUSD[baseCurrency] || 1.0
      const targetRateFromUSD = ratesToUSD[selectedCurrency] || 1.0
      
      const convertedPrice = (basePrice * rateInUSD) / targetRateFromUSD
      return {
        numeric: convertedPrice,
        string: `${convertedPrice.toFixed(2)} ${selectedCurrency}`
      }
    }
  }

  // 3. Absolute fallback: convert from the item's fallback base price property
  return {
    numeric: parseFloat(product.price || 0),
    string: `${Number(product.price || 0).toFixed(2)} ${selectedCurrency}`
  }
}

// 🌟 DYNAMICALLY COMPUTE THE ABSOLUTE COMBINED CART VALUATION (Fixes white screen)
const cartTotalDisplayPrice = computed(() => {
  const selectedCurrency = cartStore.currentCurrency
  
  const total = cartStore.items.reduce((sum, item) => {
    const qty = item.item_quantity || item.quantity || 0
    const priceInfo = getItemDisplayPrice(item)
    return sum + (priceInfo.numeric * qty)
  }, 0)

  return `${total.toFixed(2)} ${selectedCurrency}`
})
</script>