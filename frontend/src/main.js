import { createApp } from 'vue'
import { createPinia } from 'pinia'
import axios from 'axios'
import App from './App.vue'
import router from './router'
import { useAuthStore } from './stores/auth'
import './assets/style.css'

// In dev, Vite proxy handles /api/* -> 127.0.0.1:8000.
// In production (Vercel), VITE_API_URL points at the deployed Django backend.
axios.defaults.baseURL = import.meta.env.VITE_API_URL || '/'
const existingToken = localStorage.getItem('token')
if (existingToken) {
  axios.defaults.headers.common['Authorization'] = 'Token ' + existingToken
}

// Auth tokens expire (AUTH_TOKEN_MAX_AGE_DAYS) and can be revoked from another
// device. Previously only /me/ cleared the session, so an expired token left the
// user "logged in" with every page failing. One interceptor handles it globally.
let pinia = null
axios.interceptors.response.use(
  (response) => response,
  (error) => {
    const status = error.response?.status
    const url = error.config?.url || ''

    // A rejected login/register is a 400, but treat those endpoints as
    // off-limits anyway: clearing the session there would wipe the form the
    // customer is still filling in.
    const isAuthEndpoint = /\/api\/v1\/(login|register)\//.test(url)
    if (status === 401 && !isAuthEndpoint && pinia) {
      const auth = useAuthStore(pinia)
      if (auth.token) {
        auth.setSession('', null)
        // Only bounce to login if the user is not already there.
        if (router.currentRoute.value.name !== 'LogIn') {
          router.push({ path: '/log-in', query: { redirect: router.currentRoute.value.fullPath } })
        }
      }
    }
    return Promise.reject(error)
  }
)

const app = createApp(App)

pinia = createPinia()
app.use(pinia)
app.use(router)

app.mount('#app')
