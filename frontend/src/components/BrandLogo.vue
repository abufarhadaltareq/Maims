<template>
  <router-link to="/" class="inline-flex items-center gap-2.5 group select-none" aria-label="Maims — go to homepage">
    <!-- Monogram badge -->
    <svg
      :class="size === 'sm' ? 'h-8 w-8' : 'h-10 w-10'"
      class="shrink-0"
      viewBox="0 0 40 40"
      fill="none"
      aria-hidden="true"
    >
      <defs>
        <linearGradient id="maimsLogoGrad" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stop-color="#4f46e5" />
          <stop offset="0.5" stop-color="#9333ea" />
          <stop offset="1" stop-color="#ec4899" />
        </linearGradient>
      </defs>
      <rect width="40" height="40" rx="12" fill="url(#maimsLogoGrad)" />
      <path
        d="M13 27.5V12.5L20 22.5L27 12.5V27.5"
        stroke="#FFFFFF"
        stroke-width="2.6"
        stroke-linecap="round"
        stroke-linejoin="round"
      />
    </svg>

    <!-- Wordmark + tagline -->
    <span class="flex flex-col leading-none">
      <span
        class="brand-wordmark font-semibold uppercase text-gray-900 transition-colors group-hover:text-black"
        :class="size === 'sm' ? 'text-base' : 'text-lg'"
      >
        MA<span class="text-brand-accent">I</span>MS
      </span>
      <span
        v-if="showTagline"
        class="hidden sm:block mt-1 font-semibold uppercase text-gray-400"
        :class="size === 'sm' ? 'text-[0.5rem] tracking-[0.3em]' : 'text-[0.55rem] tracking-[0.4em]'"
      >
        {{ tagline }}
      </span>
    </span>
  </router-link>
</template>

<script setup>
import { BRAND_CONFIG } from '../brand.config'

defineProps({
  size: { type: String, default: 'md' }, // 'md' | 'sm'
  showTagline: { type: Boolean, default: true },
})

const tagline = BRAND_CONFIG.tagline || 'Premium Fashion'
</script>

<style scoped>
/* Elegant serif wordmark — falls back to a system serif if the web font is unavailable. */
.brand-wordmark {
  font-family: 'Playfair Display', Georgia, 'Times New Roman', serif;
  letter-spacing: 0.2em;
}
</style>
