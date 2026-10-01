<template>
  <div class="max-w-md mx-auto my-12 p-8 bg-white rounded-xl shadow-lg border border-gray-100">
    <h2 class="text-3xl font-black text-gray-800 mb-2 text-center">Welcome Back</h2>
    <p class="text-sm text-gray-500 text-center mb-6">Log in to track orders & check out faster.</p>

    <form @submit.prevent="submitForm" class="space-y-4">
      <div>
        <label class="block text-sm font-bold text-gray-700 mb-1">Username or Email</label>
        <input
          type="text"
          v-model="identifier"
          class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:outline-none"
          placeholder="Your username or email"
          autocomplete="username"
          required
        >
      </div>

      <div>
        <label class="block text-sm font-bold text-gray-700 mb-1">Password</label>
        <input
          type="password"
          v-model="password"
          class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:outline-none"
          placeholder="••••••••"
          autocomplete="current-password"
          required
        >
      </div>

      <div v-if="error" class="p-3 bg-red-50 border-l-4 border-red-500 text-red-700 text-sm rounded">
        {{ error }}
      </div>

      <button
        type="submit"
        :disabled="auth.loading"
        class="w-full py-3 bg-blue-600 hover:bg-blue-700 disabled:bg-blue-300 text-white font-bold rounded-lg transition dynamic-shadow mt-2"
      >
        {{ auth.loading ? 'Logging in…' : 'Log In' }}
      </button>
    </form>

    <p class="text-sm text-gray-600 text-center mt-6">
      Don't have an account yet?
      <router-link to="/sign-up" class="text-blue-600 hover:underline font-semibold">Sign Up</router-link>
    </p>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const router = useRouter()
const route = useRoute()
const auth = useAuthStore()

const identifier = ref('')
const password = ref('')
const error = ref('')

const submitForm = async () => {
  error.value = ''
  try {
    await auth.login(identifier.value.trim(), password.value)
    router.push(route.query.redirect || '/')
  } catch {
    error.value = auth.error
  }
}
</script>
