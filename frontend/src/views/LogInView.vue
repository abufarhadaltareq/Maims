<template>
  <div class="max-w-md mx-auto my-12 p-8 bg-white rounded-xl shadow-lg border border-gray-100">
    <h2 class="text-3xl font-black text-gray-800 mb-6 text-center">Welcome Back</h2>

    <form @submit.prevent="submitForm" class="space-y-4">
      <div>
        <label class="block text-sm font-bold text-gray-700 mb-1">Username</label>
        <input 
          type="text" 
          v-model="username" 
          class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:outline-none"
          placeholder="Your username"
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
        Log In
      </button>
    </form>

    <p class="text-sm text-gray-600 text-center mt-6">
      Don't have an account yet? 
      <router-link to="/sign-up" class="text-blue-600 hover:underline font-semibold">Sign Up</router-link>
    </p>
  </div>
</template>

<script>
import axios from 'axios'

export default {
  name: 'LogInView',
  data() {
    return {
      username: '',
      password: '',
      error: ''
    }
  },
  methods: {
    async submitForm() {
      this.error = ''
      
      const formData = {
        username: this.username,
        password: this.password
      }

      try {
        const response = await axios.post('/api/v1/login/', formData)
        
        // Save token and username to browser storage
        const token = response.data.token
        localStorage.setItem('token', token)
        localStorage.setItem('username', this.username)
        
        // Tie the token to Axios for all outgoing requests
        axios.defaults.headers.common['Authorization'] = 'Token ' + token
        
        // Redirect home or back to where they came from
        this.$router.push('/')
      } catch (err) {
        if (err.response && err.response.data && err.response.data.non_field_errors) {
          this.error = err.response.data.non_field_errors[0]
        } else {
          this.error = 'Unable to log in with provided credentials. Please try again.'
        }
      }
    }
  }
}
</script>