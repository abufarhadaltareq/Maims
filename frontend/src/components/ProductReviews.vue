<script setup>
/**
 * Product reviews: star summary, the written reviews, and the write form.
 *
 * Two things this component is careful about:
 *  - Only a signed-in customer can write, so the form prompts to sign in rather
 *    than failing after submission.
 *  - Reviews are shown with a first name and last initial, never a full name.
 */
import { ref, computed, watch, onMounted } from 'vue'
import axios from 'axios'
import { useAuthStore } from '../stores/auth'

const props = defineProps({
  productSlug: { type: String, required: true }
})

const auth = useAuthStore()

const reviews = ref([])
const breakdown = ref({})
const averageRating = ref(null)
const reviewCount = ref(0)
const loading = ref(true)
const loadError = ref('')

const submitting = ref(false)
const formError = ref('')
const editing = ref(false)
const myReviewId = ref(null)
const form = ref({ rating: 5, title: '', comment: '' })
const hoveredStar = ref(0)

const stars = [1, 2, 3, 4, 5]

const sortedBreakdown = computed(() =>
  stars.map((star) => ({
    star,
    count: breakdown.value[String(star)] || 0,
    percent: reviewCount.value
      ? Math.round(((breakdown.value[String(star)] || 0) / reviewCount.value) * 100)
      : 0
  }))
)

const canReview = computed(() => auth.isAuthenticated)
const myReview = computed(() => reviews.value.find((r) => r.id === myReviewId.value) || null)

const loadReviews = async () => {
  loading.value = true
  loadError.value = ''
  try {
    const res = await axios.get(`/api/v1/products/${props.productSlug}/reviews/`)
    reviews.value = res.data.reviews || []
    breakdown.value = res.data.breakdown || {}
    averageRating.value = res.data.average_rating
    reviewCount.value = res.data.review_count || 0
  } catch (err) {
    loadError.value = 'Reviews could not be loaded right now.'
  } finally {
    loading.value = false
  }
}

// Editing an existing review should prefill the form rather than look new.
const startEdit = (review) => {
  form.value = { rating: review.rating, title: review.title || '', comment: review.comment }
  myReviewId.value = review.id
  editing.value = true
}

const resetForm = () => {
  form.value = { rating: 5, title: '', comment: '' }
  myReviewId.value = null
  editing.value = false
  formError.value = ''
}

const submitReview = async () => {
  if (!form.value.comment.trim()) {
    formError.value = 'Please write a short comment.'
    return
  }
  submitting.value = true
  formError.value = ''
  try {
    await axios.post(`/api/v1/products/${props.productSlug}/reviews/`, {
      ...form.value,
      // The server treats a repeat review as an edit only when asked to.
      force_update: myReviewId.value != null
    })
    await loadReviews()
    resetForm()
  } catch (err) {
    if (err.response?.status === 401) {
      formError.value = 'Please sign in to leave a review.'
    } else if (err.response?.status === 409) {
      formError.value = 'You have already reviewed this product. Edit your review below instead.'
    } else {
      formError.value = err.response?.data?.error || 'Your review could not be saved.'
    }
  } finally {
    submitting.value = false
  }
}

const deleteReview = async (review) => {
  try {
    await axios.delete(`/api/v1/reviews/${review.id}/`)
    if (myReviewId.value === review.id) resetForm()
    await loadReviews()
  } catch {
    formError.value = 'That review could not be removed.'
  }
}

// Switching products (the detail page is reused) must reload, not show stale data.
watch(() => props.productSlug, loadReviews)
onMounted(loadReviews)

defineExpose({ loadReviews })
</script>

<template>
  <section id="reviews" class="mt-16 pt-12 border-t border-gray-100">
    <h2 class="text-2xl font-bold text-brand-primary mb-6">Customer reviews</h2>

    <div v-if="loading" class="text-sm text-gray-500">Loading reviews…</div>
    <div v-else-if="loadError" class="text-sm text-red-500">{{ loadError }}</div>

    <template v-else>
      <!-- Summary -->
      <div class="grid grid-cols-1 sm:grid-cols-[auto_1fr] gap-8 mb-10">
        <div class="text-center sm:text-left">
          <p class="text-5xl font-bold text-brand-primary leading-none">
            {{ averageRating != null ? Number(averageRating).toFixed(1) : '—' }}
          </p>
          <div class="flex gap-0.5 mt-2 justify-center sm:justify-start" aria-hidden="true">
            <span
              v-for="star in stars"
              :key="star"
              class="text-lg"
              :class="averageRating != null && star <= Math.round(averageRating) ? 'text-amber-400' : 'text-gray-200'"
            >★</span>
          </div>
          <p class="text-sm text-gray-500 mt-1">
            {{ reviewCount }} review{{ reviewCount === 1 ? '' : 's' }}
          </p>
        </div>

        <ul v-if="reviewCount" class="space-y-1 self-center">
          <li v-for="row in sortedBreakdown" :key="row.star" class="flex items-center gap-3 text-sm">
            <span class="w-10 shrink-0 text-gray-500">{{ row.star }} star</span>
            <span class="flex-1 h-2 rounded-full bg-gray-100 overflow-hidden">
              <span class="block h-full bg-amber-400" :style="{ width: row.percent + '%' }"></span>
            </span>
            <span class="w-8 shrink-0 text-right text-gray-400">{{ row.count }}</span>
          </li>
        </ul>
        <p v-else class="self-center text-sm text-gray-500">
          No reviews yet — yours would be the first.
        </p>
      </div>

      <!-- Write form -->
      <div class="mb-10 p-5 rounded-2xl bg-brand-muted/40 border border-brand-primary/10">
        <h3 class="font-semibold text-brand-primary mb-3">
          {{ myReview ? 'Edit your review' : 'Write a review' }}
        </h3>

        <p v-if="!canReview" class="text-sm text-gray-600">
          <RouterLink to="/log-in" class="underline">Sign in</RouterLink> to leave a review.
        </p>

        <form v-else class="space-y-4" @submit.prevent="submitReview">
          <div>
            <span class="block text-xs font-bold uppercase tracking-wider text-gray-500 mb-1">Your rating</span>
            <div class="flex items-center gap-1">
              <button
                v-for="star in stars"
                :key="star"
                type="button"
                class="text-2xl leading-none transition"
                :class="(hoveredStar || form.rating) >= star ? 'text-amber-400' : 'text-gray-200'"
                :aria-label="`${star} star${star > 1 ? 's' : ''}`"
                @mouseenter="hoveredStar = star"
                @mouseleave="hoveredStar = 0"
                @click="form.rating = star"
              >★</button>
              <span class="ml-2 text-sm text-gray-500">{{ form.rating }} of 5</span>
            </div>
          </div>

          <div>
            <label class="block text-xs font-bold uppercase tracking-wider text-gray-500 mb-1" for="review-title">
              Headline <span class="font-normal normal-case">(optional)</span>
            </label>
            <input
              id="review-title"
              v-model="form.title"
              maxlength="120"
              placeholder="Sum it up in a few words"
              class="w-full border border-gray-200 rounded-lg p-2.5 text-sm focus:outline-blue-600"
            />
          </div>

          <div>
            <label class="block text-xs font-bold uppercase tracking-wider text-gray-500 mb-1" for="review-comment">
              Your review
            </label>
            <textarea
              id="review-comment"
              v-model="form.comment"
              rows="4"
              maxlength="2000"
              placeholder="What did you like or dislike? How did the size fit?"
              class="w-full border border-gray-200 rounded-lg p-2.5 text-sm focus:outline-blue-600"
            ></textarea>
          </div>

          <p v-if="formError" class="text-sm text-red-500">{{ formError }}</p>

          <div class="flex items-center gap-3">
            <button
              type="submit"
              :disabled="submitting"
              class="px-5 py-2.5 rounded-full bg-brand-primary text-white text-sm font-medium hover:opacity-90 disabled:opacity-50"
            >
              {{ submitting ? 'Saving…' : myReview ? 'Update review' : 'Publish review' }}
            </button>
            <button
              v-if="myReview"
              type="button"
              class="text-sm text-gray-500 underline"
              @click="resetForm"
            >
              Cancel
            </button>
          </div>
        </form>
      </div>

      <!-- The reviews themselves -->
      <ul v-if="reviews.length" class="space-y-6">
        <li v-for="review in reviews" :key="review.id" class="border-b border-gray-100 pb-6 last:border-0">
          <div class="flex flex-wrap items-center gap-2 mb-1">
            <span class="flex gap-0.5" :aria-label="`${review.rating} out of 5 stars`">
              <span
                v-for="star in stars"
                :key="star"
                class="text-sm"
                :class="star <= review.rating ? 'text-amber-400' : 'text-gray-200'"
              >★</span>
            </span>
            <strong v-if="review.title" class="text-sm text-brand-primary">{{ review.title }}</strong>
          </div>
          <p class="text-xs text-gray-400 mb-2">
            {{ review.author }}
            <span v-if="review.is_verified_purchase" class="ml-1 text-emerald-600">· Verified purchase</span>
            · {{ new Date(review.created_at).toLocaleDateString() }}
          </p>
          <p class="text-sm text-brand-text/80 whitespace-pre-line">{{ review.comment }}</p>
          <button
            v-if="review.id === myReviewId"
            type="button"
            class="mt-2 text-xs text-red-500 underline"
            @click="deleteReview(review)"
          >
            Delete my review
          </button>
        </li>
      </ul>
      <p v-else class="text-sm text-gray-500">No reviews for this product yet.</p>
    </template>
  </section>
</template>