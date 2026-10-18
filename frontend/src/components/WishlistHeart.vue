<template>
  <button
    type="button"
    :aria-label="isSaved ? 'Remove from wishlist' : 'Save to wishlist'"
    :aria-pressed="isSaved"
    @click.stop.prevent="toggleWishlist"
    :class="['relative w-12 h-12 rounded-full grid place-items-center z-30 bg-white shadow-lg shadow-slate-900/25 border-2 border-white transition-all duration-200 hover:scale-110 hover:shadow-xl hover:shadow-slate-900/30 active:scale-95 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-rose-400 focus-visible:ring-offset-2', className]"
  >
    <!-- Filled heart (saved) — pops on save for instant feedback -->
    <svg
      v-if="isSaved"
      class="wl-pop w-5 h-5 text-rose-600"
      fill="currentColor"
      viewBox="0 0 24 24"
      aria-hidden="true"
    >
      <path d="M12 21.35l-1.45-1.32C5.4 15.36 2 12.28 2 8.5 2 5.42 4.42 3 7.5 3c1.74 0 3.41 0.81 4.5 2.09C13.09 3.81 14.76 3 16.5 3 19.58 3 22 5.42 22 8.5c0 3.78-3.4 6.86-8.55 11.54L12 21.35z"/>
    </svg>
    <!-- Outline heart (unsaved) -->
    <svg
      v-else
      class="w-5 h-5 text-[var(--color-content-secondary)] transition-colors"
      fill="none"
      stroke="currentColor"
      stroke-width="2.2"
      viewBox="0 0 24 24"
      aria-hidden="true"
    >
      <path stroke-linecap="round" stroke-linejoin="round" d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z"/>
    </svg>

    <!-- Toast feedback. Placed above the heart by default so the product
         card's overflow-hidden image container can't clip it; the product
         page (heart near the TOP of a tall overflow-hidden image) passes
         tip-below instead. -->
    <Transition name="wl-tip">
      <span
        v-if="flash"
        role="status"
        class="wl-tip absolute left-1/2 z-40 pointer-events-none
               text-[11px] font-bold text-white bg-[var(--color-brand)] px-2.5 py-1.5 rounded-lg
               shadow-lg whitespace-nowrap"
        :class="tipBelow ? 'top-full mt-2 wl-tip-below' : 'bottom-full mb-2 wl-tip-above'"
      >
        {{ flash }}
      </span>
    </Transition>
  </button>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useWishlistStore } from '../stores/wishlist'
import { useAuthStore } from '../stores/auth'

const props = defineProps({
  product: { type: Object, required: true },
  /** Render the toast below the heart (product page: heart sits at the top
      of an overflow-hidden image, so an above-heart toast would be clipped). */
  tipBelow: { type: Boolean, default: false },
  /** Extra classes to wrap the heart button (e.g. for placement under
      the add-to-cart button). */
  className: { type: String, default: '' },
})

const wishlist = useWishlistStore()
const auth = useAuthStore()
const flash = ref(null)
let flashTimer = null

const productId = computed(() => props.product?.id)
const isSaved = computed(() => wishlist.savedIds.has(Number(productId.value)))

function showFlash(message) {
  flash.value = message
  if (flashTimer) clearTimeout(flashTimer)
  flashTimer = setTimeout(() => { flash.value = null }, 2200)
}

async function toggleWishlist() {
  if (!productId.value) return
  if (flashTimer) { clearTimeout(flashTimer); flashTimer = null; flash.value = null }

  try {
    if (isSaved.value) {
      await wishlist.remove(productId.value)
      showFlash('Removed from wishlist')
    } else {
      await wishlist.add(props.product)
      // Guests keep the item locally (no API 401 → no login bounce) and get
      // a nudge to sign in so the wishlist syncs across devices.
      showFlash(auth.isAuthenticated ? 'Saved to wishlist' : 'Saved — sign in to keep it')
    }
  } catch {
    showFlash('Could not save this item')
  }
}
</script>

<style scoped>
/* Toast slide-in. Scoped keyframes referenced by a scoped class — the old
   version used a Tailwind arbitrary `animate-[fade-in]` pointing at a
   keyframe name Vue had already renamed for scoping, so the animation never
   ran and the toast stayed stuck at opacity-0 (invisible feedback). */
.wl-tip {
  transform: translateX(-50%);
  transition: opacity 0.18s ease-out, transform 0.18s ease-out;
}
.wl-tip-leave-active {
  transition-duration: 0.14s;
}
.wl-tip-above.wl-tip-enter-from {
  transform: translate(-50%, 6px);
}
.wl-tip-below.wl-tip-enter-from {
  transform: translate(-50%, -6px);
}
.wl-tip-enter-from,
.wl-tip-leave-to {
  opacity: 0;
}

/* Heart pop on save. */
.wl-pop {
  animation: wl-pop 0.35s cubic-bezier(0.2, 0.9, 0.3, 1.4);
}
@keyframes wl-pop {
  0%   { transform: scale(0.4); }
  55%  { transform: scale(1.35); }
  100% { transform: scale(1); }
}
</style>