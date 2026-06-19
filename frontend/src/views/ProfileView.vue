<template>
  <div class="max-w-2xl mx-auto my-12 p-6">
    <div class="bg-white rounded-2xl shadow-md border border-gray-100 overflow-hidden text-left">
      
      <div class="bg-gray-800 text-white px-8 py-6">
        <h1 class="text-2xl font-black uppercase tracking-tight">Your Profile</h1>
        <p class="text-sm text-gray-400 mt-1">Manage your account information and default shipping address.</p>
      </div>

      <div v-if="loading" class="p-8 text-center text-gray-500 font-medium">
        Loading your profile details...
      </div>

      <form v-else @submit.prevent="saveProfile" class="p-8 space-y-6">
        
        <div class="grid grid-cols-1 md:grid-cols-2 gap-6 bg-gray-50 p-4 rounded-xl border border-gray-100">
          <div>
            <label class="block text-xs font-black text-gray-400 uppercase tracking-wider mb-1">Username</label>
            <p class="font-bold text-gray-800">{{ profile.username }}</p>
          </div>
          <div>
            <label class="block text-xs font-black text-gray-400 uppercase tracking-wider mb-1">Email Address</label>
            <p class="font-bold text-gray-800">{{ profile.email }}</p>
          </div>
        </div>

        <hr class="border-gray-100" />

        <h3 class="text-sm font-black text-gray-700 uppercase tracking-wide">Default Shipping Address</h3>
        
        <div class="space-y-4">
          <div>
            <label class="block text-xs font-bold text-gray-500 uppercase mb-1">Phone Number</label>
            <input 
              v-model="profile.phone" 
              type="text" 
              class="w-full px-4 py-2.5 rounded-lg border border-gray-200 focus:outline-none focus:border-blue-600 font-medium text-sm transition"
              placeholder="e.g., +351 912 345 678"
            />
          </div>

          <div>
            <label class="block text-xs font-bold text-gray-500 uppercase mb-1">Street Address</label>
            <input 
              v-model="profile.address" 
              type="text" 
              class="w-full px-4 py-2.5 rounded-lg border border-gray-200 focus:outline-none focus:border-blue-600 font-medium text-sm transition"
              placeholder="e.g., Rua Augusta, Nº 100"
            />
          </div>

          <div class="grid grid-cols-2 gap-4">
            <div>
              <label class="block text-xs font-bold text-gray-500 uppercase mb-1">Zip Code</label>
              <input 
                v-model="profile.zipcode" 
                type="text" 
                class="w-full px-4 py-2.5 rounded-lg border border-gray-200 focus:outline-none focus:border-blue-600 font-medium text-sm transition"
                placeholder="e.g., 1100-053"
              />
            </div>
            <div>
              <label class="block text-xs font-bold text-gray-500 uppercase mb-1">City / Place</label>
              <input 
                v-model="profile.place" 
                type="text" 
                class="w-full px-4 py-2.5 rounded-lg border border-gray-200 focus:outline-none focus:border-blue-600 font-medium text-sm transition"
                placeholder="e.g., Lisbon"
              />
            </div>
          </div>
        </div>

        <div v-if="message" :class="`p-3 rounded-lg text-sm font-bold text-center ${isError ? 'bg-red-50 text-red-600' : 'bg-green-50 text-green-600'}`">
          {{ message }}
        </div>

        <div class="pt-2">
          <button 
            type="submit" 
            :disabled="saving"
            class="w-full bg-blue-600 text-white py-3 rounded-lg font-black uppercase text-sm tracking-wider hover:bg-blue-700 disabled:bg-gray-300 transition shadow-sm"
          >
            {{ saving ? 'Saving Changes...' : 'Save Profile Defaults' }}
          </button>
        </div>

      </form>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import axios from 'axios'

const profile = ref({
  username: '',
  email: '',
  phone: '',
  address: '',
  zipcode: '',
  place: ''
})

const loading = ref(true)
const saving = ref(false)
const message = ref('')
const isError = ref(false)

const fetchProfile = async () => {
  try {
    const response = await axios.get('/api/v1/profile/')
    profile.value = response.data
  } catch (error) {
    console.error('Error loading profile:', error)
  } finally {
    loading.value = false
  }
}

const saveProfile = async () => {
  saving.value = true
  message.value = ''
  isError.value = false
  
  try {
    const response = await axios.put('/api/v1/profile/', profile.value)
    profile.value = response.data
    message.value = 'Profile updated successfully!'
    
    // Clear success message after 3 seconds
    setTimeout(() => { message.value = '' }, 3000)
  } catch (error) {
    console.error('Error saving profile:', error)
    isError.value = true
    message.value = 'Failed to update profile. Please try again.'
  } finally {
    saving.value = false
  }
}

onMounted(() => {
  fetchProfile()
})
</script>