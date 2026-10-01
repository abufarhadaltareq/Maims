import { createApp } from 'vue'
import { createPinia } from 'pinia'
import axios from 'axios'
import App from './App.vue'
import router from './router'
import './assets/style.css'

// In dev, Vite proxy handles /api/* -> 127.0.0.1:8000.
// In production (Vercel), VITE_API_URL points at the deployed Django backend.
axios.defaults.baseURL = import.meta.env.VITE_API_URL || '/'
const existingToken = localStorage.getItem('token')
if (existingToken) {
  axios.defaults.headers.common['Authorization'] = 'Token ' + existingToken
}

const app = createApp(App)

app.use(createPinia())
app.use(router)

app.mount('#app')