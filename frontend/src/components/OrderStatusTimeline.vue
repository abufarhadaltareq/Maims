<script setup>
/**
 * Customer-facing status timeline for a single order.
 *
 * Mirrors the backend's fulfilment flow (see Order.STATUS_CHOICES). A declined or
 * cancelled order is terminal, so it gets its own presentation rather than a
 * progress bar that can never reach 100%.
 */
import { computed } from 'vue'

const props = defineProps({
  order: { type: Object, required: true }
})

const STEPS = [
  { key: 'new', label: 'Order placed', hint: 'We have your order' },
  { key: 'accepted', label: 'Confirmed', hint: 'The shop accepted it' },
  { key: 'packed', label: 'Packed', hint: 'Ready for the courier' },
  { key: 'shipped', label: 'On the way', hint: 'Handed to the courier' },
  { key: 'delivered', label: 'Delivered', hint: 'Enjoy!' }
]

const isStopped = computed(() =>
  ['rejected', 'cancelled', 'returned'].includes(props.order.status)
)

const stopCopy = computed(() => {
  const map = {
    rejected: {
      title: 'We could not take this order',
      detail: props.order.rejection_reason || 'Please contact us if you think this is a mistake.'
    },
    cancelled: {
      title: 'This order was cancelled',
      detail: 'Nothing further will be shipped. Contact us if you did not expect this.'
    },
    returned: {
      title: 'This order was returned',
      detail: 'The items came back to us. Any refund is on its way back to your payment method.'
    }
  }
  return map[props.order.status] || null
})

// Index of the step the order has reached. Unknown/future statuses fall back to 0
// so the timeline never renders as empty or all-complete by accident.
const currentIndex = computed(() => {
  const index = STEPS.findIndex((step) => step.key === props.order.status)
  return index === -1 ? 0 : index
})

const isDone = (step) => STEPS.findIndex((s) => s.key === step.key) <= currentIndex.value
</script>

<template>
  <div class="p-6 border-b border-gray-100 bg-white">
    <!-- Declined / cancelled / returned -->
    <div v-if="isStopped" class="rounded-xl border border-red-200 bg-red-50 p-4">
      <p class="font-bold text-red-800">{{ stopCopy.title }}</p>
      <p class="text-sm text-red-700 mt-1">{{ stopCopy.detail }}</p>
      <p class="text-xs text-red-600 mt-2">Order placed {{ new Date(order.created_at).toLocaleDateString() }}</p>
    </div>

    <!-- Normal progress -->
    <template v-else>
      <div class="flex items-center justify-between gap-2 mb-3">
        <h3 class="text-xs font-black text-gray-400 uppercase tracking-wider">Progress</h3>
        <span class="text-xs font-bold text-brand-primary">{{ order.status_label }}</span>
      </div>

      <ol class="flex items-start">
        <li
          v-for="(step, i) in STEPS"
          :key="step.key"
          class="flex-1 flex flex-col items-center text-center relative"
        >
          <!-- Connector to the next step -->
          <span
            v-if="i < STEPS.length - 1"
            class="absolute top-3 left-1/2 w-full h-0.5 -z-10"
            :class="i < currentIndex ? 'bg-brand-primary' : 'bg-gray-200'"
            aria-hidden="true"
          ></span>

          <span
            class="w-6 h-6 rounded-full flex items-center justify-center text-[11px] font-black border-2"
            :class="isDone(step)
              ? 'bg-brand-primary border-brand-primary text-white'
              : 'bg-white border-gray-200 text-gray-400'"
          >
            <span v-if="isDone(step)">✓</span>
            <span v-else>{{ i + 1 }}</span>
          </span>

          <span
            class="mt-2 text-[11px] font-bold leading-tight"
            :class="step.key === order.status ? 'text-brand-primary' : 'text-gray-500'"
          >
            {{ step.label }}
          </span>
          <span class="hidden sm:block text-[10px] text-gray-400 leading-tight mt-0.5">{{ step.hint }}</span>
        </li>
      </ol>

      <p v-if="order.tracking_number" class="mt-4 text-sm text-gray-600">
        <span class="font-bold text-gray-700">Tracking number:</span>
        <span class="font-mono">{{ order.tracking_number }}</span>
      </p>
    </template>
  </div>
</template>