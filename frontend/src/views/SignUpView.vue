<template>
  <div class="max-w-md mx-auto my-12 p-8 bg-white rounded-xl shadow-lg border border-gray-100">
    <h2 class="text-3xl font-black text-gray-800 mb-2 text-center">Create an Account</h2>
    <p class="text-sm text-gray-500 text-center mb-6">Join Maims for faster checkout & order tracking.</p>

    <form @submit.prevent="submitForm" class="space-y-4">
      <div class="grid grid-cols-2 gap-3">
        <div>
          <label class="block text-sm font-bold text-gray-700 mb-1">First Name</label>
          <input
            type="text"
            v-model="first_name"
            class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:outline-none"
            placeholder="Amina"
          >
        </div>
        <div>
          <label class="block text-sm font-bold text-gray-700 mb-1">Last Name</label>
          <input
            type="text"
            v-model="last_name"
            class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:outline-none"
            placeholder="Khan"
          >
        </div>
      </div>

      <div>
        <label class="block text-sm font-bold text-gray-700 mb-1">Username</label>
        <input
          type="text"
          v-model="username"
          class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:outline-none"
          placeholder="Choose a username"
          required
        >
      </div>

      <div>
        <label class="block text-sm font-bold text-gray-700 mb-1">Email Address</label>
        <input
          type="email"
          v-model="email"
          class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:outline-none"
          placeholder="you@example.com"
          required
        >
      </div>

      <div>
        <label class="block text-sm font-bold text-gray-700 mb-1">Password</label>
        <input
          type="password"
          v-model="password"
          class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:outline-none"
          placeholder="Min. 8 characters"
          minlength="8"
          required
        >
        <p class="text-[11px] text-gray-400 mt-1">Min. 8 characters. Avoid common passwords like "password123".</p>
      </div>

      <div v-if="error" class="p-3 bg-red-50 border-l-4 border-red-500 text-red-700 text-sm rounded">
        {{ error }}
      </div>

      <button
        type="submit"
        :disabled="auth.loading"
        class="w-full py-3 bg-blue-600 hover:bg-blue-700 disabled:bg-blue-300 text-white font-bold rounded-lg transition dynamic-shadow mt-2"
      >
        {{ auth.loading ? 'Creating account…' : 'Sign Up' }}
      </button>
    </form>

    <p class="text-sm text-gray-600 text-center mt-6">
      Already have an account?
      <router-link to="/log-in" class="text-blue-600 hover:underline font-semibold">Log In</router-link>
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

const first_name = ref('')
const last_name = ref('')
const username = ref('')
const email = ref('')
const password = ref('')
const error = ref('')

const submitForm = async () => {
  error.value = ''
  try {
    await auth.register({
      username: username.value.trim(),
      email: email.value.trim(),
      password: password.value,
      first_name: first_name.value.trim(),
      last_name: last_name.value.trim(),
    })
    router.push(route.query.redirect || '/')
  } catch {
    error.value = auth.error
  }
}
</script>
