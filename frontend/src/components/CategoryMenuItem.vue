<template>
  <div
    class="category-menu-item"
    @mouseenter="onMouseEnter"
    @mouseleave="onMouseLeave"
  >
    <div
      class="flex items-center gap-3 rounded-lg transition-colors"
      :class="isOpen ? 'bg-white/10' : 'hover:bg-white/10'"
    >
      <router-link
        :to="`/category/${category.slug}`"
        class="flex min-w-0 flex-1 items-center gap-3 rounded-lg p-2 focus-visible:outline focus-visible:outline-2 focus-visible:outline-white"
        @click="$emit('navigate')"
      >
        <img
          v-if="category.image_url"
          :src="category.image_url"
          :alt="`${category.name} category`"
          loading="lazy"
          class="shrink-0 rounded-md bg-white/10 object-cover"
          :class="root ? 'h-14 w-14' : 'h-11 w-11'"
        />
        <span
          v-else
          class="flex shrink-0 items-center justify-center rounded-md bg-white/10 font-semibold text-slate-300"
          :class="root ? 'h-14 w-14 text-lg' : 'h-11 w-11 text-sm'"
          aria-hidden="true"
        >{{ category.name.slice(0, 1).toUpperCase() }}</span>
        <span class="min-w-0 flex-1">
          <span
            class="block truncate"
            :class="root ? 'text-sm font-semibold uppercase tracking-wide text-white' : 'text-sm font-medium text-slate-200'"
          >{{ category.name }}</span>
          <span v-if="category.product_count" class="mt-0.5 block text-xs text-slate-400">
            {{ category.product_count }} {{ category.product_count === 1 ? 'item' : 'items' }}
          </span>
        </span>
      </router-link>
      <button
        v-if="category.children?.length"
        type="button"
        class="mr-2 flex h-9 w-9 shrink-0 items-center justify-center rounded-full text-slate-300 transition-colors hover:bg-white/10 hover:text-white focus-visible:outline focus-visible:outline-2 focus-visible:outline-white"
        :aria-expanded="isOpen"
        :aria-label="`${isOpen ? 'Hide' : 'Show'} ${category.name} subcategories`"
        @click.stop="toggleChildren"
      >
        {{ isOpen ? '−' : '+' }}
      </button>
    </div>
    <div
      v-if="category.children?.length && isOpen"
      class="ml-4 mt-1 border-l border-white/15 py-1 pl-2 sm:ml-6 sm:pl-3"
    >
      <CategoryMenuItem
        v-for="child in category.children"
        :key="child.slug"
        :category="child"
        @navigate="$emit('navigate')"
      />
    </div>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'

defineProps({
  category: { type: Object, required: true },
  root: { type: Boolean, default: false },
})
defineEmits(['navigate'])

const expanded = ref(false)
const hovered = ref(false)
const suppressHoverUntilLeave = ref(false)
const isOpen = computed(() => expanded.value || hovered.value)

const onMouseEnter = () => {
  if (!suppressHoverUntilLeave.value) hovered.value = true
}

const onMouseLeave = () => {
  hovered.value = false
  suppressHoverUntilLeave.value = false
}

const toggleChildren = () => {
  if (isOpen.value) {
    expanded.value = false
    hovered.value = false
    suppressHoverUntilLeave.value = true
    return
  }
  expanded.value = true
  suppressHoverUntilLeave.value = false
}
</script>
