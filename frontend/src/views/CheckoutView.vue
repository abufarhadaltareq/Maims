<script setup>
import { ref, onMounted, computed } from 'vue'
import { CURRENCIES, useCartStore } from '../stores/cart'
import { useSiteStore } from '../stores/site'
import axios from 'axios'
import { loadStripe } from '@stripe/stripe-js'
import { getCartDeliveryFee, getProductDisplayPrice } from '../utils/pricing.js'

// --- State ---
const cartStore = useCartStore()
const site = useSiteStore()
const isSuccess = ref(false)
const successMethod = ref('stripe')
const successOrderId = ref(null)
const successWhatsappLink = ref('')
const isProcessing = ref(false)
const serverError = ref('')
const orderId = ref(null)
const stripe = ref(null)
const cardElement = ref(null)
const stripeReady = ref(false)
const paymentMethod = ref('stripe') // stripe | paypal | whatsapp

// --- Idempotency ---
// One key per checkout attempt. It stays the same for every retry of the SAME
// attempt (double-clicked button, flaky connection, an axios retry) and is only
// regenerated once an order succeeds. The backend resolves a repeated key to the
// order it already created, so a retry can never produce a duplicate order,
// double-decrement stock, or charge the card twice for one basket.
const idempotencyKey = ref('')

const newIdempotencyKey = () =>
  globalThis.crypto?.randomUUID
    ? globalThis.crypto.randomUUID()
    : `maims-${Date.now().toString(36)}-${Math.random().toString(36).slice(2)}`

// Same body, different header: the backend reads the key from the header only.
const postCheckout = (paymentMethodValue) =>
  axios.post(
    '/api/v1/checkout/',
    { ...basePayload.value, payment_method: paymentMethodValue },
    { headers: { 'Idempotency-Key': idempotencyKey.value } }
  )

// --- Form Data ---
const form = ref({
  first_name: '',
  last_name: '',
  email: '',
  country_code: '+351',
  phone: '',
  address: '',
  place: '',
  zipcode: '',
  // WhatsApp Business may only open a conversation with someone who asked for
  // it, so this stays opt-in and is re-checked on the server before every send.
  whatsapp_opt_in: false,
  // Email-marketing consent for the address above. Only sent when the admin
  // shows the checkbox; its default state follows the consent strategy
  // (unticked unless the shop deliberately chose opt-out).
  marketing_opt_in: false
})

// --- Computed ---
const supportedCurrencies = computed(() =>
  CURRENCIES.filter(({ code }) =>
    cartStore.items.length > 0 && cartStore.items.every((item) =>
      item.product?.prices?.some((price) => String(price.currency).toUpperCase() === code)
    )
  )
)
const browserCurrency = (() => {
  const region = navigator.language?.match(/-([A-Za-z]{2})(?:-|$)/)?.[1]?.toUpperCase() || ''
  const euroRegions = new Set([
    'AT', 'BE', 'CY', 'DE', 'EE', 'ES', 'FI', 'FR', 'GR', 'HR', 'IE', 'IT',
    'LT', 'LU', 'LV', 'MT', 'NL', 'PT', 'SI', 'SK',
  ])
  if (euroRegions.has(region)) return 'EUR'
  return { BD: 'BDT', PK: 'PKR', SE: 'SEK', US: 'USD' }[region] || 'EUR'
})()
const stripeCurrency = computed(() => {
  const available = supportedCurrencies.value.map(({ code }) => code)
  if (available.includes(browserCurrency)) return browserCurrency
  if (available.includes('EUR')) return 'EUR'
  return available[0] || 'EUR'
})
const checkoutCurrency = computed(() =>
  paymentMethod.value === 'stripe' ? stripeCurrency.value : cartStore.currentCurrency
)
const itemPrice = (item) =>
  getProductDisplayPrice(item.product || {}, checkoutCurrency.value).numeric
const checkoutSubtotal = computed(() =>
  cartStore.items.reduce((sum, item) => sum + itemPrice(item) * (Number(item.quantity) || 0), 0)
)
const totalCartCost = computed(() =>
  checkoutSubtotal.value + getCartDeliveryFee(cartStore.items, checkoutCurrency.value)
)
const currencySupported = computed(() =>
  supportedCurrencies.value.some(({ code }) => code === checkoutCurrency.value)
)

const formattedItems = computed(() => {
  return cartStore.items.map(item => ({
    product_id: item.product.id,
    quantity: item.quantity || 1,
    price: itemPrice(item).toFixed(2),
    selectedSize: item.size || '',
    variant: item.variant || item.size || ''
  }))
})

const basePayload = computed(() => ({
  first_name: form.value.first_name,
  last_name: form.value.last_name,
  email: form.value.email,
  phone: `${form.value.country_code} ${form.value.phone}`,
  address: form.value.address,
  zipcode: form.value.zipcode,
  place: form.value.place,
  total_amount: totalCartCost.value.toFixed(2),
  currency: checkoutCurrency.value,
  items: formattedItems.value,
  whatsapp_opt_in: form.value.whatsapp_opt_in,
  marketing_opt_in: form.value.marketing_opt_in,
}))

const initializeStripe = async () => {
  if (!site.stripeEnabled) return
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
    stripeReady.value = true
  } catch (err) {
    serverError.value = 'Unable to initialize payment form.'
    console.error(err)
  }
}

onMounted(async () => {
  idempotencyKey.value = newIdempotencyKey()
  await site.fetchSettings()
  // Checkout consent box default: ticked only for the opt-out strategy, and
  // only if the admin is showing the box at all.
  if (site.newsletterCheckoutEnabled && site.newsletterBoxTicked) {
    form.value.marketing_opt_in = true
  }
  // Default to first available method if admin disabled Stripe.
  if (!site.stripeEnabled && site.paypalEnabled) paymentMethod.value = 'paypal'
  else if (!site.stripeEnabled && !site.paypalEnabled && site.whatsappEnabled) paymentMethod.value = 'whatsapp'
  try {
    const response = await axios.get('/api/v1/profile/')
    if (response.data) {
      form.value = { ...form.value, ...response.data }
    }
  } catch (error) {
    console.warn('Profile not loaded (this is fine if no user is logged in).')
  }

  if (site.stripeEnabled) await initializeStripe()
})

const submitCheckoutForm = async () => {
  isProcessing.value = true
  serverError.value = ''

  if (!cartStore.items.length) {
    serverError.value = 'Your bag is empty.'
    isProcessing.value = false
    return
  }

  if (!currencySupported.value) {
    serverError.value = supportedCurrencies.value.length
      ? `Some items are not available in ${checkoutCurrency.value}. Choose ${supportedCurrencies.value.map(({ code }) => code).join(', ')} to continue.`
      : 'These items do not have a common checkout currency. Please review your bag or contact the store.'
    isProcessing.value = false
    return
  }

  // PayPal / WhatsApp: no card details collected here — the order is created
  // unpaid (stock reserved) and payment is completed outside this page.
  if (paymentMethod.value === 'paypal' || paymentMethod.value === 'whatsapp') {
    try {
      const res = await postCheckout(paymentMethod.value)
      successMethod.value = res.data.payment_method || paymentMethod.value
      successOrderId.value = res.data.order_id
      successWhatsappLink.value = res.data.whatsapp_link || ''
      cartStore.clearCart()
      // A completed order must not reuse this key; the next basket is a new order.
      idempotencyKey.value = newIdempotencyKey()
      isSuccess.value = true
    } catch (err) {
      serverError.value = err.response?.data?.error || 'Could not place your order. Please try again.'
    } finally {
      isProcessing.value = false
    }
    return
  }

  if (!stripe.value || !cardElement.value) {
    serverError.value = 'Payment provider is not ready. Please refresh and try again.'
    isProcessing.value = false
    return
  }

  try {
    const checkoutResponse = await postCheckout('stripe')

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
      successMethod.value = 'stripe'
      successOrderId.value = orderId.value
      idempotencyKey.value = newIdempotencyKey()
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
      <p v-if="successOrderId" class="text-xs font-bold text-gray-400 uppercase tracking-widest">Order #{{ successOrderId }}</p>
      <p class="text-gray-500 text-sm max-w-sm mx-auto">
        <span v-if="successMethod === 'stripe'">Your payment has been successfully completed. We are preparing your packages for shipment.</span>
        <span v-else-if="successMethod === 'paypal'">Your order is reserved. The shop will contact you to arrange PayPal payment; payment is not processed automatically.</span>
        <span v-else>Your order is saved. Tap below to send it to us on WhatsApp and confirm.</span>
      </p>
      <a
        v-if="successMethod === 'whatsapp' && successWhatsappLink"
        :href="successWhatsappLink"
        target="_blank" rel="noopener"
        class="block bg-gradient-brand text-white font-bold px-6 py-3.5 rounded-xl hover:brightness-95 transition shadow-sm"
      >
        Send Order on WhatsApp
      </a>
      <div class="flex gap-3">
        <router-link to="/" class="flex-1 block bg-gradient-brand text-white font-bold px-6 py-3.5 rounded-xl hover:brightness-110 transition shadow-sm">
          Continue Shopping
        </router-link>
        <router-link to="/order-history" class="flex-1 block bg-gray-100 text-gray-800 font-bold px-6 py-3.5 rounded-xl hover:bg-gray-200 transition shadow-sm">
          Track Order
        </router-link>
      </div>
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
                <input type="text" v-model="form.first_name" required class="w-full border border-gray-200 rounded-lg p-2.5 text-sm focus:outline-brand" />
              </div>
              <div>
                <label class="block text-xs font-bold uppercase tracking-wider text-gray-500 mb-1">Last Name</label>
                <input type="text" v-model="form.last_name" required class="w-full border border-gray-200 rounded-lg p-2.5 text-sm focus:outline-brand" />
              </div>
            </div>

            <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label class="block text-xs font-bold uppercase tracking-wider text-gray-500 mb-1">Email Address</label>
                <input type="email" v-model="form.email" required class="w-full border border-gray-200 rounded-lg p-2.5 text-sm focus:outline-brand" />
                <label v-if="site.newsletterCheckoutEnabled" class="mt-2 flex items-start gap-2 text-xs text-gray-600 cursor-pointer">
                  <input
                    type="checkbox"
                    v-model="form.marketing_opt_in"
                    class="mt-0.5 rounded border-gray-300 text-brand-accent focus:ring-brand-accent"
                  />
                  <span>
                    {{ site.newsletterConsentText }}
                    <span class="block text-gray-500">
                      We'll only use this address for the emails you asked for.
                      Opt out any time from any message.
                    </span>
                  </span>
                </label>
              </div>
              <div>
                <label class="block text-xs font-bold uppercase tracking-wider text-gray-500 mb-1">Phone Number</label>
                <div class="flex gap-2">
                  <input type="text" v-model="form.country_code" required class="w-24 border border-gray-200 rounded-lg p-2.5 text-sm text-center focus:outline-brand" />
                  <input type="tel" v-model="form.phone" required class="flex-1 border border-gray-200 rounded-lg p-2.5 text-sm focus:outline-brand" />
                </div>
                <label class="mt-2 flex items-start gap-2 text-xs text-gray-600 cursor-pointer">
                  <input
                    type="checkbox"
                    v-model="form.whatsapp_opt_in"
                    class="mt-0.5 rounded border-gray-300 text-brand-accent focus:ring-brand-accent"
                  />
                  <span>
                    Send me order updates on WhatsApp at this number
                    <span class="block text-gray-500">
                      We'll text you when your order is accepted, packed, shipped and delivered.
                      Opt out any time by replying STOP.
                    </span>
                  </span>
                </label>
              </div>
            </div>

            <input type="text" v-model="form.address" placeholder="Address" required class="w-full border border-gray-200 rounded-lg p-2.5 text-sm focus:outline-brand" />

            <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <input type="text" v-model="form.place" placeholder="City" required class="w-full border border-gray-200 rounded-lg p-2.5 text-sm focus:outline-brand" />
              <input type="text" v-model="form.zipcode" placeholder="Zipcode" required class="w-full border border-gray-200 rounded-lg p-2.5 text-sm focus:outline-brand" />
            </div>
          </div>

          <div class="bg-white border border-gray-100 rounded-xl p-6 shadow-sm space-y-4">
            <h2 class="text-xl font-bold tracking-tight mb-2">Payment Method</h2>
            <div class="grid grid-cols-1 sm:grid-cols-3 gap-3">
              <button
                v-if="site.stripeEnabled"
                type="button"
                @click="paymentMethod = 'stripe'"
                :class="paymentMethod === 'stripe' ? 'border-brand bg-purple-50' : 'border-gray-200'"
                class="border-2 rounded-xl p-3 text-left transition"
              >
                <p class="font-bold text-sm">💳 Card</p>
                <p class="text-[11px] text-gray-500">Visa / Mastercard via Stripe</p>
              </button>
              <button
                v-if="site.paypalEnabled"
                type="button"
                @click="paymentMethod = 'paypal'"
                :class="paymentMethod === 'paypal' ? 'border-brand bg-purple-50' : 'border-gray-200'"
                class="border-2 rounded-xl p-3 text-left transition"
              >
                <p class="font-bold text-sm">🅿️ PayPal</p>
                <p class="text-[11px] text-gray-500">Pay with your PayPal account</p>
              </button>
              <button
                v-if="site.whatsappEnabled"
                type="button"
                @click="paymentMethod = 'whatsapp'"
                :class="paymentMethod === 'whatsapp' ? 'border-brand bg-purple-50' : 'border-gray-200'"
                class="border-2 rounded-xl p-3 text-left transition"
              >
                <p class="font-bold text-sm">💬 WhatsApp Order</p>
                <p class="text-[11px] text-gray-500">Confirm on chat</p>
              </button>
            </div>
            <p v-if="!site.stripeEnabled && !site.paypalEnabled && !site.whatsappEnabled" class="text-sm text-red-500">
              No payment methods are enabled. Please contact the store.
            </p>
          </div>

          <div v-if="paymentMethod === 'stripe'" class="bg-white border border-gray-100 rounded-xl p-6 shadow-sm space-y-4">
            <h2 class="text-xl font-bold tracking-tight mb-4">Payment Details</h2>
            <div id="card-element" class="p-3.5 border border-gray-200 rounded-lg bg-gray-50/50"></div>
            <p class="text-[11px] text-gray-400">Secured by Stripe. We never store your card number.</p>
            <p v-if="serverError" class="text-sm text-red-500">{{ serverError }}</p>
          </div>
          <div v-else class="bg-purple-50 border border-blue-100 rounded-xl p-5 text-sm text-blue-900">
            <p v-if="paymentMethod === 'paypal'" class="font-semibold">Your order will be reserved while the shop contacts you to arrange PayPal payment. Payment is handled manually and no automatic PayPal link is sent yet.</p>
            <p v-else class="font-semibold">No card needed — your order is saved, then sent to our WhatsApp Business number with one tap.</p>
            <p v-if="serverError" class="text-sm text-red-500 mt-2">{{ serverError }}</p>
          </div>

          <div v-if="!currencySupported" class="rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">
            <p v-if="supportedCurrencies.length">
              This cart can be checked out in
              <button
                v-for="currency in supportedCurrencies"
                :key="currency.code"
                type="button"
                class="mx-1 font-bold underline"
                @click="cartStore.setCurrency(currency.code)"
              >{{ currency.code }}</button>
              only. Choose an available currency to continue.
            </p>
            <p v-else>These items have no currency in common for checkout. Remove an item or contact the store.</p>
          </div>

          <button type="submit" :disabled="isProcessing" class="w-full bg-gradient-brand text-white font-bold py-4 rounded-xl hover:brightness-110 transition disabled:opacity-70">
            <span v-if="isProcessing">Processing...</span>
            <span v-else-if="paymentMethod === 'stripe'">Pay {{ totalCartCost.toFixed(2) }} {{ checkoutCurrency }}</span>
            <span v-else-if="paymentMethod === 'paypal'">Place PayPal Order · {{ totalCartCost.toFixed(2) }} {{ checkoutCurrency }}</span>
            <span v-else>Place WhatsApp Order · {{ totalCartCost.toFixed(2) }} {{ checkoutCurrency }}</span>
          </button>
        </form>

        <div class="lg:col-span-5 bg-gray-50 border border-gray-100 rounded-xl p-6 space-y-4 text-left">
          <h2 class="font-bold text-lg tracking-tight mb-4">Review Your Bag</h2>
          <p v-if="paymentMethod === 'stripe'" class="rounded-lg border border-blue-200 bg-blue-50 p-3 text-sm text-blue-900">
            Stripe will charge in {{ checkoutCurrency }}, selected from your browser locale and available product prices. Your storefront display currency ({{ cartStore.currentCurrency }}) is unchanged.
          </p>
          <div v-for="item in cartStore.items" :key="`${item.product.id}-${item.variant || item.size || 'default'}`" class="flex justify-between py-2 border-b">
            <div>
              <span class="font-semibold">{{ item.product.name }}</span>
              <p v-if="item.variant || item.size" class="text-xs text-gray-500">{{ item.variant || `Size: ${item.size}` }}</p>
            </div>
            <span>{{ (itemPrice(item) * (item.quantity || 0)).toFixed(2) }} {{ checkoutCurrency }}</span>
          </div>
          <div class="flex justify-between text-sm pt-2">
            <span>Delivery</span>
            <span>{{ getCartDeliveryFee(cartStore.items, checkoutCurrency).toFixed(2) }} {{ checkoutCurrency }}</span>
          </div>
          <div class="flex justify-between font-bold text-xl pt-4">
            <span>Total including delivery:</span>
            <span>{{ totalCartCost.toFixed(2) }} {{ checkoutCurrency }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>