<template>
  <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-10 font-brand text-brand-text">
    <!-- Header -->
    <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-8">
      <div>
        <p class="text-[11px] uppercase tracking-[0.3em] text-brand-accent font-bold mb-1.5">Wishlist</p>
        <h1 class="text-2xl sm:text-3xl font-extrabold tracking-tight">Saved for later</h1>
        <p class="text-gray-500 text-sm mt-1">{{ wishlist.count }} item{{ wishlist.count === 1 ? '' : 's' }} saved</p>
      </div>
      <button
        v-if="wishlist.items.length"
        @click="clearAll"
        class="text-xs font-bold text-rose-600 hover:text-rose-700 underline underline-offset-2 transition"
      >
        Clear all
      </button>
    </div>

    <!-- Empty state -->
    <div v-if="wishlist.items.length === 0" class="text-center py-24 border border-dashed border-gray-200 rounded-3xl bg-gray-50/60">
      <div class="w-16 h-16 mx-auto mb-5 rounded-full bg-slate-100 flex items-center justify-center text-slate-400">
        <svg class="w-8 h-8" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
          <path d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z"/>
        </svg>
      </div>
      <h2 class="text-xl font-bold text-slate-800 mb-2">Nothing saved yet</h2>
      <p class="text-gray-500 text-sm mb-6">Heart any product to save it here for later.</p>
      <router-link
        to="/"
        class="inline-block bg-[var(--color-brand)] text-white font-bold px-7 py-3.5 rounded-full hover:bg-[var(--color-brand)]/80 transition"
      >
        Browse collections
      </router-link>
    </div>

    <!-- Saved items -->
    <div v-else class="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-5 sm:gap-6">
      <ProductCard
        v-for="row in wishlist.items"
        :key="`wl-${row.product.id}`"
        :product="row.product"
      />
    </div>
  </div>
</template>

<script setup>
import { onMounted } from 'vue'
import ProductCard from '../components/ProductCard.vue'
import { useWishlistStore } from '../stores/wishlist'

const wishlist = useWishlistStore()

async function clearAll() {
  await wishlist.clearAll() // purges server rows too, or they resurrect on sync
}

onMounted(() => {
  wishlist.hydrate()
})
</script>