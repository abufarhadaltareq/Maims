<template>
  <div class="max-w-md mx-auto my-12 p-8 bg-white rounded-xl shadow-lg border border-gray-100">
    <h2 class="text-3xl font-black text-gray-800 mb-2 text-center">Forgot your password?</h2>
    <p class="text-sm text-gray-500 text-center mb-6">
      Enter the email of your account and we'll send you a link to set a new password.
    </p>

    <form v-if="!sent" @submit.prevent="submitForm" class="space-y-4">
      <div>
        <label class="block text-sm font-bold text-gray-700 mb-1">Email</label>
        <input
          type="email"
          v-model="email"
          class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:outline-none"
          placeholder="you@example.com"
          autocomplete="email"
          required
        >
      </div>

      <div v-if="error" class="p-3 bg-red-50 border-l-4 border-red-500 text-red-700 text-sm rounded">
        {{ error }}
      </div>

      <button
        type="submit"
        :disabled="loading"
        class="w-full py-3 bg-blue-600 hover:bg-blue-700 disabled:bg-blue-300 text-white font-bold rounded-lg transition dynamic-shadow mt-2"
      >
        {{ loading ? 'Sending…' : 'Send reset link' }}
      </button>
    </form>

    <div v-else class="p-4 bg-emerald-50 border-l-4 border-emerald-500 text-emerald-800 text-sm rounded mb-4">
      If an account with <b>{{ email }}</b> exists, a reset link is on its way.
      The link stays valid for 24 hours — check your inbox (and spam folder).
    </div>

    <p class="text-sm text-gray-600 text-center mt-6">
      Remembered it?
      <router-link to="/log-in" class="text-blue-600 hover:underline font-semibold">Back to log in</router-link>
    </p>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import axios from 'axios'

const email = ref('')
const loading = ref(false)
const sent = ref(false)
const error = ref('')

const submitForm = async () => {
  error.value = ''
  loading.value = true
  try {
    await axios.post('/api/v1/password-reset/', { email: email.value.trim() })
    sent.value = true
  } catch (e) {
    error.value = e?.response?.data?.error || 'Something went wrong. Please try again.'
  } finally {
    loading.value = false
  }
}
</script>
