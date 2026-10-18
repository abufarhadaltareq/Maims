<template>
  <router-link
    :to="to"
    :href="href"
    class="inline-block bg-gradient-brand text-white font-bold px-8 py-3.5 rounded-full shadow-brand hover:brightness-105 transition active:scale-95"
  >
    <slot>Explore Collections</slot>
  </router-link>
</template>

<script setup>
defineProps({
  to: { type: String, default: '/' },
  href: { type: String, default: '' },
})
</script>
