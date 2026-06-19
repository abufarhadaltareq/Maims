import { createApp } from 'vue'
import { createPinia } from 'pinia'
import axios from 'axios'
import App from './App.vue'
import router from './router'
import './assets/style.css'

axios.defaults.baseURL = '/'
const existingToken = localStorage.getItem('token')
if (existingToken) {
  axios.defaults.headers.common['Authorization'] = 'Token ' + existingToken
}

const app = createApp(App)

app.use(createPinia())
app.use(router)

app.mount('#app')