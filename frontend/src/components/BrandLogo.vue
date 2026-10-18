<template>
  <router-link to="/" class="inline-flex items-center gap-2.5 group select-none" :aria-label="`${storeName} — go to homepage`">
    <!-- Uploaded brand logo (PNG/JPG from Admin → Site settings). Falls back to the monogram.
         Sizing is responsive: smaller on small screens so it always fits the header. -->
    <img
      v-if="logoUrl"
      :src="logoUrl"
      :alt="`${storeName} logo`"
      :class="size === 'sm'
        ? 'h-7 sm:h-8 max-w-[6rem] sm:max-w-[7rem]'
        : 'h-8 sm:h-10 max-w-[7rem] sm:max-w-[9rem]'"
      class="shrink-0 object-contain"
      @error="logoBroken = true"
    />
    <!-- Monogram badge -->
    <svg
      v-else
      :class="size === 'sm' ? 'h-7 w-7 sm:h-8 sm:w-8' : 'h-8 w-8 sm:h-10 sm:w-10'"
      class="shrink-0"
      viewBox="0 0 40 40"
      fill="none"
      aria-hidden="true"
    >
      <defs>
        <linearGradient id="maimsLogoGrad" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stop-color="#1e293b" />
          <stop offset="0.55" stop-color="#0ea5e9" />
          <stop offset="1" stop-color="#38bdf8" />
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
        class="brand-wordmark font-semibold uppercase text-[var(--color-brand)] transition-colors group-hover:[color:var(--color-brand)]"
        :class="size === 'sm' ? 'text-base' : 'text-lg'"
      >
        {{ wordmarkStart }}<span class="transition-colors group-hover:[color:var(--color-brand)]">{{ wordmarkAccent }}</span>{{ wordmarkEnd }}
      </span>
      <span
        v-if="showTagline && tagline"
        class="hidden sm:block mt-1 font-semibold uppercase text-[var(--color-brand)]/70"
        :class="size === 'sm' ? 'text-[0.5rem] tracking-[0.3em]' : 'text-[0.55rem] tracking-[0.4em]'"
      >
        {{ tagline }}
      </span>
    </span>
  </router-link>
</template>

<script setup>
import { computed, ref } from 'vue'
import { BRAND_CONFIG } from '../brand.config'
import { useSiteStore } from '../stores/site'

defineProps({
  size: { type: String, default: 'md' }, // 'md' | 'sm'
  showTagline: { type: Boolean, default: true },
})

const site = useSiteStore()

// Hide a broken upload (deleted file, bad URL) instead of showing a broken image.
const logoBroken = ref(false)
const logoUrl = computed(() => (logoBroken.value ? '' : site.logoUrl))

const storeName = computed(() => site.storeName || BRAND_CONFIG.name || 'Maims')

// Split the store name so the middle letter keeps the accent treatment,
// whatever the shop is renamed to. Short names render whole.
const wordmarkStart = computed(() => {
  const upper = storeName.value.toUpperCase()
  if (upper.length <= 2) return upper
  return upper.slice(0, 2)
})
const wordmarkAccent = computed(() => {
  const upper = storeName.value.toUpperCase()
  if (upper.length <= 2) return ''
  return upper.slice(2, 3)
})
const wordmarkEnd = computed(() => {
  const upper = storeName.value.toUpperCase()
  if (upper.length <= 2) return ''
  return upper.slice(3)
})

const tagline = computed(() => site.tagline || BRAND_CONFIG.tagline || 'Premium Fashion')
</script>

<style scoped>
/* Elegant serif wordmark — falls back to a system serif if the web font is unavailable. */
.brand-wordmark {
  font-family: 'Playfair Display', Georgia, 'Times New Roman', serif;
  letter-spacing: 0.2em;
}
</style>
