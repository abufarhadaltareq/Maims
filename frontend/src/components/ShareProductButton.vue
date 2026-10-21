<template>
  <div class="inline-flex flex-col items-end gap-1">
    <button
      type="button"
      @click.stop="shareProduct"
      :disabled="isSharing"
      class="inline-flex min-h-9 items-center justify-center gap-2 border border-black/20 px-3 text-xs font-semibold text-black transition hover:bg-black hover:text-white disabled:opacity-50"
      :aria-label="`Share ${product.name}`"
    >
      <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.8" d="M12 16V4m0 0L7.5 8.5M12 4l4.5 4.5M5 13v5a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2v-5" />
      </svg>
      Share
    </button>
    <span v-if="message" role="status" class="max-w-44 text-right text-[10px] text-gray-500">{{ message }}</span>
  </div>
</template>

<script setup>
import { ref } from 'vue'

const props = defineProps({
  product: { type: Object, required: true },
})

const isSharing = ref(false)
const message = ref('')
let messageTimer

const showMessage = (text) => {
  message.value = text
  clearTimeout(messageTimer)
  messageTimer = setTimeout(() => { message.value = '' }, 5000)
}

const copyLink = async (url) => {
  if (!navigator.clipboard?.writeText) return false
  try {
    await navigator.clipboard.writeText(url)
    return true
  } catch {
    return false
  }
}

const shareProduct = async () => {
  if (isSharing.value) return
  isSharing.value = true
  message.value = ''
  const url = new URL(`/products/${props.product.slug}`, window.location.origin).href
  const imageUrl = props.product.get_image || props.product.get_thumbnail
  const shareData = {
    title: props.product.name,
    text: props.product.name,
    url,
  }

  try {
    if (imageUrl && navigator.share && navigator.canShare) {
      const response = await fetch(imageUrl)
      if (!response.ok) throw new Error('Product image could not be loaded.')
      const blob = await response.blob()
      const extension = blob.type.split('/')[1]?.replace('jpeg', 'jpg') || 'jpg'
      const image = new File([blob], `${props.product.slug || 'product'}.${extension}`, {
        type: blob.type || 'image/jpeg',
      })
      const imageShare = { ...shareData, files: [image] }
      if (navigator.canShare(imageShare)) {
        await navigator.share(imageShare)
        return
      }
    }

    if (navigator.share) {
      await navigator.share(shareData)
      showMessage('Shared product link. Image sharing is not supported by this app.')
      return
    }

    const copied = await copyLink(url)
    if (imageUrl) {
      const link = document.createElement('a')
      link.href = imageUrl
      link.download = `${props.product.slug || 'product'}.jpg`
      link.target = '_blank'
      link.rel = 'noopener'
      link.click()
    }
    showMessage(copied
      ? 'Product link copied; image download started.'
      : 'Sharing is unavailable in this browser.')
  } catch (error) {
    if (error?.name === 'AbortError') return
    const copied = await copyLink(url)
    showMessage(copied
      ? 'Image sharing was unavailable; product link copied instead.'
      : error?.message || 'Unable to share this product.')
  } finally {
    isSharing.value = false
  }
}
</script>
