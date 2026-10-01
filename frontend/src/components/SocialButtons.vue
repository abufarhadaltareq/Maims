<template>
  <!-- Floating social dock: WhatsApp chat + admin-controlled social pages -->
  <div class="fixed bottom-5 right-5 z-40 flex flex-col items-end gap-3 print:hidden">
    <a
      v-if="site.whatsappEnabled"
      :href="whatsappLink"
      target="_blank"
      rel="noopener"
      title="Chat with us on WhatsApp"
      class="group flex items-center gap-2 bg-[#25D366] hover:brightness-95 text-white text-sm font-bold pl-3 pr-4 py-2.5 rounded-full shadow-lg transition"
    >
      <SocialIcon name="whatsapp" class="w-6 h-6" />
      <span class="hidden sm:inline">WhatsApp</span>
    </a>

    <a
      v-for="link in site.socialLinks"
      :key="link.key"
      :href="link.url"
      target="_blank"
      rel="noopener"
      :title="`Visit our ${link.label}`"
      class="flex items-center gap-2 text-white text-sm font-bold pl-3 pr-4 py-2.5 rounded-full shadow-lg transition hover:brightness-110"
      :class="DOCK_COLORS[link.key] || 'bg-gray-700'"
    >
      <SocialIcon :name="link.key" class="w-6 h-6" />
      <span class="hidden sm:inline">{{ link.label }}</span>
    </a>
  </div>
</template>

<script setup>
import { computed, onMounted } from 'vue'
import { useSiteStore } from '../stores/site'
import SocialIcon from './SocialIcon.vue'

const site = useSiteStore()

const whatsappLink = computed(() =>
  site.whatsappBaseLink || site.whatsappOrderLink()
)

// Background colours for the floating dock buttons.
const DOCK_COLORS = {
  facebook: 'bg-[#1877F2]',
  instagram: 'bg-gradient-to-tr from-[#feda75] via-[#d62976] to-[#4f5bd5]',
  tiktok: 'bg-black',
  twitter: 'bg-black',
  youtube: 'bg-[#FF0000]',
  linkedin: 'bg-[#0A66C2]',
}

onMounted(() => {
  site.fetchSettings()
})
</script>
