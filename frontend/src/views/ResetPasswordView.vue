<template>
  <div class="max-w-md mx-auto my-12 p-8 bg-purple-500/10 backdrop-blur-md rounded-2xl shadow-xl border border-purple-500/20">
    <h2 class="text-3xl font-black text-gray-800 mb-2 text-center">Choose a new password</h2>
    <p class="text-sm text-gray-500 text-center mb-6">
      Your reset link is valid for 24 hours.
    </p>

    <form v-if="!done" @submit.prevent="submitForm" class="space-y-4">
      <div>
        <label class="block text-sm font-bold text-gray-700 mb-1">New password</label>
        <input
          type="password"
          v-model="newPassword"
          class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-brand focus:outline-none"
          placeholder="At least 8 characters"
          autocomplete="new-password"
          minlength="8"
          required
        >
      </div>

      <div>
        <label class="block text-sm font-bold text-gray-700 mb-1">Confirm new password</label>
        <input
          type="password"
          v-model="confirmPassword"
          class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-brand focus:outline-none"
          placeholder="Repeat it"
          autocomplete="new-password"
          minlength="8"
          required
        >
      </div>

      <div v-if="error" class="p-3 bg-red-50 border-l-4 border-red-500 text-red-700 text-sm rounded">
        {{ error }}
      </div>

      <button
        type="submit"
        :disabled="loading"
        class="w-full py-3 bg-gradient-brand hover:brightness-110 disabled:opacity-50 text-white font-bold rounded-lg transition dynamic-shadow mt-2"
      >
        {{ loading ? 'Updating…' : 'Set new password' }}
      </button>
    </form>

    <div v-else class="p-4 bg-emerald-50 border-l-4 border-emerald-500 text-emerald-800 text-sm rounded mb-4">
      Your password has been updated. You can now log in with your new password.
    </div>

    <p class="text-sm text-gray-600 text-center mt-6">
      <router-link to="/log-in" class="text-brand hover:underline font-semibold">
        {{ done ? 'Go to log in' : 'Back to log in' }}
      </router-link>
    </p>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import axios from 'axios'

const route = useRoute()
const router = useRouter()

const uid = ref((route.query.uid || '').toString())
const token = ref((route.query.token || '').toString())
const newPassword = ref('')
const confirmPassword = ref('')
const loading = ref(false)
const done = ref(false)
const error = ref('')

const submitForm = async () => {
  error.value = ''

  if (!uid.value || !token.value) {
    error.value = 'This reset link is invalid. Request a fresh one from the login page.'
    return
  }
  if (newPassword.value !== confirmPassword.value) {
    error.value = 'The two passwords do not match.'
    return
  }

  loading.value = true
  try {
    await axios.post('/api/v1/password-reset/confirm/', {
      uid: uid.value,
      token: token.value,
      new_password: newPassword.value,
    })
    done.value = true
  } catch (e) {
    error.value = e?.response?.data?.error || 'Something went wrong. Please request a new link.'
  } finally {
    loading.value = false
  }
}
</script>
