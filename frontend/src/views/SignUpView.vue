<template>
  <div class="max-w-md mx-auto my-12 p-8 bg-white rounded-xl shadow-lg border border-gray-100">
    <h2 class="text-3xl font-black text-gray-800 mb-6 text-center">Create an Account</h2>

    <form @submit.prevent="submitForm" class="space-y-4">
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
          placeholder="••••••••"
          required
        >
      </div>

      <div v-if="error" class="p-3 bg-red-50 border-l-4 border-red-500 text-red-700 text-sm rounded">
        {{ error }}
      </div>

      <button 
        type="submit" 
        class="w-full py-3 bg-blue-600 hover:bg-blue-700 text-white font-bold rounded-lg transition dynamic-shadow mt-2"
      >
        Sign Up
      </button>
    </form>

    <p class="text-sm text-gray-600 text-center mt-6">
      Already have an account? 
      <router-link to="/log-in" class="text-blue-600 hover:underline font-semibold">Log In</router-link>
    </p>
  </div>
</template>

<script>
import axios from 'axios'

export default {
  name: 'SignUpView',
  data() {
    return {
      username: '',
      email: '',
      password: '',
      error: ''
    }
  },
  methods: {
    async submitForm() {
      this.error = ''
      
      const formData = {
        username: this.username,
        email: this.email,
        password: this.password
      }

      try {
        const response = await axios.post('/api/v1/register/', formData)
        
        // Save the generated token and username instantly to the browser storage
        const token = response.data.token
        localStorage.setItem('token', token)
        localStorage.setItem('username', response.data.username)
        
        // Set Axios default authorization header for all future requests
        axios.defaults.headers.common['Authorization'] = 'Token ' + token
        
        // Take the user straight to the homepage or their account page
        this.$router.push('/')
      } catch (err) {
        if (err.response && err.response.data && err.response.data.error) {
          this.error = err.response.data.error
        } else {
          this.error = 'Something went wrong. Please try again.'
        }
      }
    }
  }
}
</script>