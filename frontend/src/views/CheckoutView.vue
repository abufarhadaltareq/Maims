<script setup>
import { ref, onMounted, computed } from 'vue'
import { useCartStore } from '../stores/cart'
import axios from 'axios'
import { loadStripe } from '@stripe/stripe-js'

// --- State ---
const cartStore = useCartStore()
const isSuccess = ref(false)
const isProcessing = ref(false)
const serverError = ref('')
const orderId = ref(null)
const stripe = ref(null)
const cardElement = ref(null)

// --- Form Data ---
const form = ref({
  first_name: '',
  last_name: '',
  email: '',
  country_code: '+351',
  phone: '',
  address: '',
  place: '',
  zipcode: ''
})

// --- Computed ---
const totalCartCost = computed(() => {
  if (!cartStore?.items) return 0
  return cartStore.items.reduce((total, item) => {
    return total + (item.product.price * item.quantity)
  }, 0)
})

const formattedItems = computed(() => {
  return cartStore.items.map(item => ({
    product_id: item.product.id,
    quantity: item.quantity,
    price: item.product.price,
    selectedSize: item.size || ''
  }))
})

const initializeStripe = async () => {
  try {
    const response = await axios.get('/api/v1/stripe-key/')
    const publishableKey = response.data.publishableKey
    stripe.value = await loadStripe(publishableKey)

    if (!stripe.value) {
      serverError.value = 'Stripe failed to initialize.'
      return
    }

    const elements = stripe.value.elements()
    cardElement.value = elements.create('card', {
      style: {
        base: {
          color: '#111827',
          fontSize: '16px',
          '::placeholder': { color: '#9ca3af' }
        },
        invalid: {
          color: '#ef4444'
        }
      }
    })
    cardElement.value.mount('#card-element')
  } catch (err) {
    serverError.value = 'Unable to initialize payment form.'
    console.error(err)
  }
}

onMounted(async () => {
  try {
    const response = await axios.get('/api/v1/profile/')
    if (response.data) {
      form.value = { ...form.value, ...response.data }
    }
  } catch (error) {
    console.warn('Profile not loaded (this is fine if no user is logged in).')
  }

  await initializeStripe()
})

const submitCheckoutForm = async () => {
  isProcessing.value = true
  serverError.value = ''

  if (!stripe.value || !cardElement.value) {
    serverError.value = 'Payment provider is not ready. Please refresh and try again.'
    isProcessing.value = false
    return
  }

  try {
    const checkoutResponse = await axios.post('/api/v1/checkout/', {
      first_name: form.value.first_name,
      last_name: form.value.last_name,
      email: form.value.email,
      phone: `${form.value.country_code} ${form.value.phone}`,
      address: form.value.address,
      zipcode: form.value.zipcode,
      place: form.value.place,
      total_amount: totalCartCost.value,
      items: formattedItems.value
    })

    const clientSecret = checkoutResponse.data.client_secret
    orderId.value = checkoutResponse.data.order_id

    const result = await stripe.value.confirmCardPayment(clientSecret, {
      payment_method: {
        card: cardElement.value,
        billing_details: {
          name: `${form.value.first_name} ${form.value.last_name}`,
          email: form.value.email,
          address: {
            line1: form.value.address,
            postal_code: form.value.zipcode,
            city: form.value.place
          }
        }
      }
    })

    if (result.error) {
      serverError.value = result.error.message || 'Payment could not be processed.'
      isProcessing.value = false
      return
    }

    if (result.paymentIntent?.status === 'succeeded') {
      await axios.post('/api/v1/checkout/confirm/', {
        order_id: orderId.value,
        payment_intent_id: result.paymentIntent.id
      })

      cartStore.clearCart()
      isSuccess.value = true
    } else {
      serverError.value = 'Payment was not completed. Please try again.'
    }
  } catch (err) {
    serverError.value = err.response?.data?.error || 'Payment failed. Please check your card details.'
    console.error(err)
  } finally {
    isProcessing.value = false
  }
}
</script>

<template>
  <div class="py-12 px-6 max-w-6xl mx-auto font-brand text-brand-text">

    <div v-if="isSuccess" class="max-w-xl mx-auto text-center py-16 px-8 bg-white border border-gray-100 rounded-2xl shadow-sm my-4 space-y-6">
      <div class="w-20 h-20 bg-emerald-50 rounded-full flex items-center justify-center mx-auto text-emerald-500">
        <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2.5" stroke="currentColor" class="w-10 h-10">
          <path stroke-linecap="round" stroke-linejoin="round" d="M4.5 12.75l6 6 9-13.5" />
        </svg>
      </div>
      <h1 class="text-3xl font-black tracking-tight text-gray-900">Thank You For Your Order!</h1>
      <p class="text-gray-500 text-sm max-w-sm mx-auto">Your payment has been successfully completed. We are preparing your packages for shipment.</p>
      <router-link to="/" class="block bg-blue-600 text-white font-bold px-6 py-3.5 rounded-xl hover:bg-blue-700 transition shadow-sm mt-4">
        Continue Shopping
      </router-link>
    </div>

    <div v-else-if="!cartStore?.items || cartStore.items.length === 0" class="text-center py-12">
      <h1 class="text-3xl font-extrabold tracking-tight mb-8">Checkout</h1>
      <p class="text-gray-500 mb-4">You don't have any items in your bag to purchase.</p>
      <router-link to="/" class="underline font-bold">Return to Shop</router-link>
    </div>

    <div v-else>
      <h1 class="text-3xl font-extrabold tracking-tight text-left mb-8">Checkout</h1>

      <div class="grid grid-cols-1 lg:grid-cols-12 gap-10 items-start">
        <form @submit.prevent="submitCheckoutForm" class="lg:col-span-7 space-y-6 text-left">

          <div class="bg-white border border-gray-100 rounded-xl p-6 shadow-sm space-y-4">
            <h2 class="text-xl font-bold tracking-tight mb-2">Shipping Information</h2>

            <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label class="block text-xs font-bold uppercase tracking-wider text-gray-500 mb-1">First Name</label>
                <input type="text" v-model="form.first_name" required class="w-full border border-gray-200 rounded-lg p-2.5 text-sm focus:outline-blue-600" />
              </div>
              <div>
                <label class="block text-xs font-bold uppercase tracking-wider text-gray-500 mb-1">Last Name</label>
                <input type="text" v-model="form.last_name" required class="w-full border border-gray-200 rounded-lg p-2.5 text-sm focus:outline-blue-600" />
              </div>
            </div>

            <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label class="block text-xs font-bold uppercase tracking-wider text-gray-500 mb-1">Email Address</label>
                <input type="email" v-model="form.email" required class="w-full border border-gray-200 rounded-lg p-2.5 text-sm focus:outline-blue-600" />
              </div>
              <div>
                <label class="block text-xs font-bold uppercase tracking-wider text-gray-500 mb-1">Phone Number</label>
                <div class="flex gap-2">
                  <input type="text" v-model="form.country_code" required class="w-24 border border-gray-200 rounded-lg p-2.5 text-sm text-center focus:outline-blue-600" />
                  <input type="tel" v-model="form.phone" required class="flex-1 border border-gray-200 rounded-lg p-2.5 text-sm focus:outline-blue-600" />
                </div>
              </div>
            </div>

            <input type="text" v-model="form.address" placeholder="Address" required class="w-full border border-gray-200 rounded-lg p-2.5 text-sm focus:outline-blue-600" />

            <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <input type="text" v-model="form.place" placeholder="City" required class="w-full border border-gray-200 rounded-lg p-2.5 text-sm focus:outline-blue-600" />
              <input type="text" v-model="form.zipcode" placeholder="Zipcode" required class="w-full border border-gray-200 rounded-lg p-2.5 text-sm focus:outline-blue-600" />
            </div>
          </div>

          <div class="bg-white border border-gray-100 rounded-xl p-6 shadow-sm space-y-4">
            <h2 class="text-xl font-bold tracking-tight mb-4">Payment Details</h2>
            <div id="card-element" class="p-3.5 border border-gray-200 rounded-lg bg-gray-50/50"></div>
            <p v-if="serverError" class="text-sm text-red-500">{{ serverError }}</p>
          </div>

          <button type="submit" :disabled="isProcessing" class="w-full bg-blue-600 text-white font-bold py-4 rounded-xl hover:bg-blue-700 transition disabled:opacity-70">
            {{ isProcessing ? 'Processing...' : `Pay ${totalCartCost.toFixed(2)} €` }}
          </button>
        </form>

        <div class="lg:col-span-5 bg-gray-50 border border-gray-100 rounded-xl p-6 space-y-4 text-left">
          <h2 class="font-bold text-lg tracking-tight mb-4">Review Your Bag</h2>
          <div v-for="item in cartStore.items" :key="`${item.product.id}-${item.size || 'default'}`" class="flex justify-between py-2 border-b">
            <div>
              <span class="font-semibold">{{ item.product.name }}</span>
              <p v-if="item.size" class="text-xs text-gray-500">Size: {{ item.size }}</p>
            </div>
            <span>{{ (item.product.price * item.quantity).toFixed(2) }} €</span>
          </div>
          <div class="flex justify-between font-bold text-xl pt-4">
            <span>Total:</span>
            <span>{{ totalCartCost.toFixed(2) }} €</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>