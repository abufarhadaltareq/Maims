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
              <input
                :value="item.quantity"
                @change="(e) => cartStore.setQuantity(item.product?.id, item.size, e.target.value)"
                type="number" min="1" max="99"
                class="w-12 text-center font-bold text-sm border border-gray-200 rounded-md py-1"
              />
              <button
                @click="cartStore.incrementQuantity(item.product?.id, item.size)"
                :disabled="item.product?.stock != null && item.quantity >= item.product.stock"
                title="Add one"
                class="w-7 h-7 flex items-center justify-center border border-gray-200 rounded-md text-gray-600 hover:bg-gray-50 active:bg-gray-100 transition text-sm font-bold disabled:opacity-40"
              >
                +
              </button>
              <button
                @click="cartStore.removeItem(item.product?.id, item.size)"
                class="ml-2 text-xs text-gray-400 hover:text-red-600 underline"
              >
                Remove
              </button>
            </div>
            <p v-if="item.product?.stock != null && item.quantity >= item.product.stock" class="text-[11px] text-amber-600 font-semibold">
              Only {{ item.product.stock }} in stock
            </p>
          </div>

          <div class="text-right pl-2">
            <p class="font-extrabold text-base whitespace-nowrap">
              {{ (getItemDisplayPrice(item).numeric * (item.quantity || 0)).toFixed(2) }} {{ cartStore.currentCurrency }}
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

        <a
          v-if="site.whatsappEnabled && whatsappCartLink"
          :href="whatsappCartLink"
          target="_blank" rel="noopener"
          class="flex items-center justify-center gap-2 w-full text-center bg-[#25D366] text-white font-bold py-3 rounded-lg shadow hover:brightness-95 transition duration-200"
        >
          <svg class="w-5 h-5" fill="currentColor" viewBox="0 0 24 24"><path d="M12 2a10 10 0 00-8.6 15.1L2 22l5-1.3A10 10 0 1012 2zm5.4 14.1c-.2.6-1.3 1.2-1.8 1.2-.5.1-1 .2-3.4-.7-2.9-1.2-4.7-4.1-4.9-4.3-.1-.2-1.2-1.6-1.2-3.1s.8-2.2 1-2.5c.3-.3.6-.4.8-.4h.6c.2 0 .4 0 .6.5s.8 1.9.8 2c.1.1.1.3 0 .5-.3.6-.6.8-.4 1.1.6 1.1 1.4 1.8 2.4 2.4.3.2.5.1.7-.1l.8-.9c.2-.3.4-.2.7-.1l2 1c.3.1.5.2.6.4 0 .1 0 .6-.5 1.5z"/></svg>
          Order via WhatsApp
        </a>
        <p v-if="site.whatsappEnabled" class="text-[11px] text-gray-400 text-center">Sends your bag as a WhatsApp message — pay on chat.</p>
      </div>

    </div>
  </div>
</template>

<script setup>
import { computed, onMounted } from 'vue'
import { useCartStore } from '../stores/cart'
import { useSiteStore } from '../stores/site'
import { getProductDisplayPrice } from '../utils/pricing.js'

const cartStore = useCartStore()
const site = useSiteStore()

const getItemDisplayPrice = (item) =>
  getProductDisplayPrice(item.product || {}, cartStore.currentCurrency)

// Single source: store getter keeps cart + checkout totals identical.
const cartTotalDisplayPrice = computed(() => {
  const { subtotal, currency } = cartStore.cartPricing
  return `${subtotal.toFixed(2)} ${currency}`
})

const waLines = computed(() =>
  cartStore.items.map((item) => {
    const qty = item.quantity || 0
    const unit = getItemDisplayPrice(item).numeric
    const size = item.size ? ` (${item.size})` : ''
    return `• ${qty} x ${item.product?.name}${size} — ${(unit * qty).toFixed(2)} ${cartStore.currentCurrency}`
  })
)

const whatsappCartLink = computed(() =>
  site.whatsappOrderLink(null, waLines.value, `Total: ${cartTotalDisplayPrice.value}`)
)

onMounted(() => {
  site.fetchSettings()
})
</script>