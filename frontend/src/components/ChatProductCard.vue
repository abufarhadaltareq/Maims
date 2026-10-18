<template>
  <router-link
    :to="`/products/${product.slug}`"
    class="block shrink-0 w-48 rounded-xl border border-gray-100 bg-white overflow-hidden flex flex-col hover:border-brand-accent hover:shadow-lg transition duration-300 group"
  >
    <div class="relative block aspect-[4/5] bg-gray-100 overflow-hidden">
      <img
        :src="product.image || 'https://placehold.co/320x400'"
        :alt="product.name"
        class="w-full h-full object-cover group-hover:scale-105 transition duration-500"
        loading="lazy"
      />
      <span v-if="product.in_stock === false || product.stock === 0" class="absolute top-2 left-2 text-[10px] font-bold text-white bg-[var(--color-brand)]/60 px-2 py-0.5 rounded">Sold out</span>
      <span v-if="product.category_name" class="absolute top-2 right-2 text-[10px] font-bold text-white bg-brand-accent/90 backdrop-blur px-2 py-0.5 rounded">{{ product.category_name }}</span>
    </div>
    <div class="p-2">
      <div class="text-[11px] font-extrabold uppercase tracking-wider text-gray-400 mb-0.5">{{ product.brand_name || 'Maims' }}</div>
      <div class="text-[12px] font-bold text-gray-800 leading-tight line-clamp-2 mb-1.5 group-hover:text-brand-accent transition">{{ product.name }}</div>
      <div class="flex items-baseline gap-1">
        <span class="text-[13px] font-extrabold text-[var(--color-content)]">{{ product.formatted_price || product.price }}</span>
        <span v-if="product.currency" class="text-[10px] text-gray-400 font-medium">{{ product.currency }}</span>
      </div>
    </div>
  </router-link>
</template>

<script setup>
defineProps({
  product: { type: Object, required: true },
})
</script>
