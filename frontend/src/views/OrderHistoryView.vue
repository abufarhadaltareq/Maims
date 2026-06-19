<template>
  <div class="max-w-4xl mx-auto my-12 p-6">
    <h1 class="text-3xl font-black text-gray-800 mb-8 text-left uppercase tracking-tight">Your Order History</h1>

    <div v-if="loading" class="text-center py-12 text-gray-500 font-medium">
      Loading your orders...
    </div>

    <div v-else-if="orders.length === 0" class="text-center py-12 bg-white rounded-xl border border-dashed border-gray-200 p-8">
      <p class="text-gray-500 mb-4 font-medium">You haven't placed any orders yet.</p>
      <router-link to="/" class="inline-block bg-blue-600 text-white px-6 py-2.5 rounded-lg font-bold text-sm hover:bg-blue-700 transition">
        Start Shopping
      </router-link>
    </div>

    <div v-else class="space-y-8">
      <div 
        v-for="order in orders" 
        :key="order.id" 
        class="bg-white rounded-xl shadow-md border border-gray-100 overflow-hidden text-left"
      >
        <div class="bg-gray-800 text-white px-6 py-4 flex flex-wrap justify-between items-center gap-4">
          <div class="flex items-center gap-6">
            <div>
              <p class="text-xs text-gray-400 font-bold uppercase tracking-wider">Order ID</p>
              <p class="text-sm font-black text-white">#{{ order.id }}</p>
            </div>
            <div>
              <p class="text-xs text-gray-400 font-bold uppercase tracking-wider">Payment Status</p>
              <span class="inline-block text-[11px] bg-green-500 text-white px-2.5 py-0.5 rounded-full font-extrabold uppercase tracking-wide">
                Paid
              </span>
            </div>
          </div>
          <div class="text-right">
            <p class="text-xs text-gray-400 font-bold uppercase tracking-wider">Grand Total</p>
            <p class="text-lg font-black text-emerald-400">{{ formatPrice(order.total_amount) }} €</p>
          </div>
        </div>

        <div class="bg-gray-50/70 px-6 py-5 border-b border-gray-100 grid grid-cols-1 md:grid-cols-2 gap-6 text-sm">
          <div>
            <h3 class="text-xs font-black text-gray-400 uppercase tracking-wider mb-2">Delivery Address</h3>
            <p class="font-bold text-gray-800">{{ order.first_name }} {{ order.last_name }}</p>
            <p class="text-gray-600 mt-0.5">{{ order.address }}</p>
            <p class="text-gray-600 font-medium">{{ order.zipcode }} - {{ order.place }}</p>
          </div>
          <div>
            <h3 class="text-xs font-black text-gray-400 uppercase tracking-wider mb-2">Contact Details</h3>
            <div class="space-y-1 text-gray-600">
              <p><span class="font-bold text-gray-700">Email:</span> {{ order.email }}</p>
              <p><span class="font-bold text-gray-700">Phone:</span> {{ order.phone }}</p>
            </div>
          </div>
        </div>

        <div class="p-6">
          <h3 class="text-xs font-black text-gray-400 uppercase tracking-wider mb-4">Items in This Shipment</h3>
          
          <div class="divide-y divide-gray-100">
            <div 
              v-for="item in order.items" 
              :key="item.id" 
              class="py-4 flex justify-between items-center first:pt-0 last:pb-0"
            >
              <div class="flex items-center gap-4">
                <div class="w-14 h-14 bg-gray-50 rounded-xl flex items-center justify-center overflow-hidden border border-gray-100 shadow-sm flex-shrink-0">
                  <img 
                    v-if="item.product && item.product.get_thumbnail" 
                    :src="item.product.get_thumbnail" 
                    alt="Product Thumbnail"
                    class="w-full h-full object-cover"
                  />
                  <span v-else class="text-xl">👕</span>
                </div>
                
                <div>
                  <router-link 
                    v-if="item.product && item.product.slug"
                    :to="`/products/${item.product.slug}`" 
                    class="font-black text-gray-900 text-base hover:text-blue-600 hover:underline transition"
                  >
                    {{ item.product.name }}
                  </router-link>
                  <p v-else class="font-black text-gray-900 text-base">
                    {{ item.product ? item.product.name : 'Unknown Product' }}
                  </p>
                  
                  <p class="text-xs text-gray-500 font-semibold mt-1">
                    Quantity: <span class="text-gray-800 font-bold bg-gray-100 px-2 py-0.5 rounded">{{ item.quantity }}</span> 
                    <span class="text-gray-300 mx-2.5">|</span> 
                    Unit Price: <span class="text-gray-700 font-medium">{{ formatPrice(item.price) }} €</span>
                  </p>
                </div>
              </div>

              <div class="text-right">
                <p class="font-black text-gray-900 text-base">
                  {{ formatPrice(item.price * item.quantity) }} €
                </p>
              </div>
            </div>
          </div>
        </div>

      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import axios from 'axios'

const orders = ref([])
const loading = ref(true)

const formatPrice = (price) => {
  const num = Number(price)
  return isNaN(num) ? '0.00' : num.toFixed(2)
}

const fetchOrders = async () => {
  try {
    const response = await axios.get('/api/v1/orders/')
    orders.value = response.data
  } catch (error) {
    console.error('Error fetching deep product parameters:', error)
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  fetchOrders()
})
</script>