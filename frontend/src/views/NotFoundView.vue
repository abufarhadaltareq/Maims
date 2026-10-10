<script setup>
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'

const route = useRoute()
const router = useRouter()

// Surface the path the visitor actually typed — it is the single most useful
// thing on a 404 and the one piece of feedback that makes typos recoverable.
const attemptedPath = computed(() => route.fullPath)

const suggestions = [
  { label: 'Shop the latest drop', to: '/' },
  { label: 'Browse new arrivals', to: '/new-arrivals' },
  { label: 'Search the store', to: '/search' },
  { label: 'View your bag', to: '/cart' }
]

const goHome = () => router.push('/')
</script>

<template>
  <!-- Catch-all route. Vue Router previously rendered an empty <RouterView> for
       an unknown URL, which looked like a broken/blank page rather than a
       missing page. -->
  <div class="font-brand text-brand-text min-h-[60vh] flex items-center justify-center px-6 py-20">
    <div class="max-w-xl text-center space-y-6">
      <p class="text-sm font-semibold tracking-[0.35em] uppercase text-brand-accent">404</p>

      <h1 class="text-3xl sm:text-4xl font-bold text-brand-primary">We couldn't find that page</h1>

      <p class="text-brand-text/70">
        The link may be out of date, or the product may have sold out and been removed.
      </p>

      <p class="text-sm text-brand-text/50 break-words">
        You tried: <span class="font-mono">{{ attemptedPath }}</span>
      </p>

      <div class="flex flex-wrap items-center justify-center gap-3 pt-2">
        <button
          type="button"
          class="px-6 py-3 rounded-full bg-brand-primary text-white font-medium hover:opacity-90 transition"
          @click="goHome"
        >
          Back to home
        </button>

        <RouterLink
          v-for="item in suggestions"
          :key="item.to"
          :to="item.to"
          class="px-4 py-2 rounded-full border border-brand-primary/20 text-brand-primary text-sm hover:bg-brand-muted transition"
        >
          {{ item.label }}
        </RouterLink>
      </div>
    </div>
  </div>
</template>
