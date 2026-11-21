<template>
  <div class="category-menu-item group">
    <div class="flex items-center justify-between gap-2">
      <router-link
        :to="`/category/${category.slug}`"
        class="min-w-0 flex-1 transition-colors hover:bg-gray-100 hover:text-black focus-visible:bg-gray-100 focus-visible:text-black"
        :class="root ? 'py-3 text-sm font-semibold uppercase tracking-wide text-black' : 'py-2 text-sm text-gray-700'"
        @click="$emit('navigate')"
      >
        {{ category.name }}
      </router-link>
      <button
        v-if="category.children?.length"
        type="button"
        class="flex h-8 w-8 shrink-0 items-center justify-center text-gray-500 transition-colors hover:bg-gray-100 hover:text-black"
        :aria-expanded="expanded"
        :aria-label="`${expanded ? 'Hide' : 'Show'} ${category.name} subcategories`"
        @click.stop="expanded = !expanded"
      >
        {{ expanded ? '−' : '+' }}
      </button>
    </div>
    <div
      v-if="category.children?.length"
      class="category-menu-children hidden border-l border-black/10 pl-3 group-hover:block group-focus-within:block"
      :class="{ 'is-expanded': expanded }"
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
import { ref } from 'vue'

defineProps({
  category: { type: Object, required: true },
  root: { type: Boolean, default: false },
})
defineEmits(['navigate'])

const expanded = ref(false)
</script>

<style scoped>
.is-expanded {
  display: block;
}
</style>
