import { defineStore } from 'pinia'
import axios from 'axios'

/**
 * Central auth state. Token lives in localStorage; axios header is kept in sync.
 * Exposes: user, isAuthenticated, login/register/logout, fetchMe, changePassword.
 */
export const useAuthStore = defineStore('auth', {
  state: () => ({
    token: localStorage.getItem('token') || '',
    user: JSON.parse(localStorage.getItem('auth_user') || 'null'),
    loading: false,
    error: '',
  }),

  getters: {
    isAuthenticated: (state) => !!state.token && !!state.user,
    username: (state) => state.user?.username || localStorage.getItem('username') || '',
  },

  actions: {
    setSession(token, user) {
      this.token = token || ''
      this.user = user || null
      this.error = ''
      if (token) {
        localStorage.setItem('token', token)
        axios.defaults.headers.common['Authorization'] = 'Token ' + token
      } else {
        localStorage.removeItem('token')
        delete axios.defaults.headers.common['Authorization']
      }
      if (user) {
        localStorage.setItem('auth_user', JSON.stringify(user))
        localStorage.setItem('username', user.username || '')
      } else {
        localStorage.removeItem('auth_user')
        localStorage.removeItem('username')
      }
    },

    async register(payload) {
      this.loading = true
      this.error = ''
      try {
        const res = await axios.post('/api/v1/register/', payload)
        this.setSession(res.data.token, res.data.user || { username: res.data.username })
        return res.data
      } catch (err) {
        this.error =
          err.response?.data?.error ||
          err.response?.data?.errors?.username?.[0] ||
          err.response?.data?.errors?.email?.[0] ||
          err.response?.data?.errors?.password?.[0] ||
          'Registration failed. Please try again.'
        throw err
      } finally {
        this.loading = false
      }
    },

    async login(identifier, password) {
      this.loading = true
      this.error = ''
      try {
        const res = await axios.post('/api/v1/login/', { username: identifier, password })
        this.setSession(res.data.token, res.data.user)
        return res.data
      } catch (err) {
        this.error = err.response?.data?.error || 'Unable to log in with provided credentials.'
        throw err
      } finally {
        this.loading = false
      }
    },

    async fetchMe() {
      if (!this.token) return null
      try {
        const res = await axios.get('/api/v1/me/')
        const user = res.data?.user || null
        if (user) {
          this.user = user
          localStorage.setItem('auth_user', JSON.stringify(user))
          localStorage.setItem('username', user.username || '')
        }
        return res.data
      } catch {
        // Token invalid/expired -> clear session so guards redirect to login.
        this.setSession('', null)
        return null
      }
    },

    async logout() {
      try {
        if (this.token) await axios.post('/api/v1/logout/')
      } catch {
        // ignore - clear locally anyway
      } finally {
        this.setSession('', null)
      }
    },

    async changePassword(current_password, new_password) {
      const res = await axios.post('/api/v1/change-password/', { current_password, new_password })
      if (res.data?.token) this.setSession(res.data.token, this.user)
      return res.data
    },
  },
})
