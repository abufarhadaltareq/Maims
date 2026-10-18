import { defineStore } from 'pinia'
import axios from 'axios'
import { useCartStore } from './cart'

export const CHATBOT_SESSION_KEY = 'maims_chatbot_session'

export const useChatbotStore = defineStore('chatbot', {
  state: () => ({
    sessionId: localStorage.getItem(CHATBOT_SESSION_KEY) || '',
    messages: [],
    suggestions: [],
    storeName: 'Maims',
    greeting: '',
    loading: false,
    error: '',
    open: false,
  }),

  getters: {
    currency: (state) => {
      const cart = useCartStore()
      return cart.currentCurrency || 'EUR'
    },
  },

  actions: {
    _ensureSession() {
      if (!this.sessionId) {
        this.sessionId = 'sess_' + Math.random().toString(36).slice(2, 14) + Date.now().toString(36)
        localStorage.setItem(CHATBOT_SESSION_KEY, this.sessionId)
      }
      return this.sessionId
    },

    async fetchSuggestions() {
      try {
        const res = await axios.get('/api/v1/chatbot/suggestions/')
        this.storeName = res.data.store_name || 'Maims'
        this.greeting = res.data.greeting || ''
        this.suggestions = res.data.suggestions || []
      } catch (err) {
        this.suggestions = [
          'Show latest arrivals',
          'Pure silk sarees under €100',
          'Track my order',
          'How long does shipping take?',
          'Chat on WhatsApp',
        ]
      }
    },

    async send(message) {
      const text = (message || '').trim()
      if (!text) return null
      if (this.loading) return null

      this._ensureSession()
      this.loading = true
      this.error = ''

      const userMsg = { role: 'user', text, createdAt: Date.now() }
      this.messages.push(userMsg)

      try {
        const res = await axios.post('/api/v1/chatbot/chat/', {
          message: text,
          session_id: this.sessionId,
          currency: this.currency,
        })

        const data = res.data || {}
        const botMsg = {
          role: 'assistant',
          text: data.reply || '',
          products: data.products || [],
          suggestions: data.suggestions || [],
          action: data.action || null,
          createdAt: Date.now(),
        }
        this.messages.push(botMsg)
        return botMsg
      } catch (err) {
        this.error = err.response?.data?.error || "I'm sorry, I couldn't reach the assistant right now. Please try again."
        const failMsg = {
          role: 'assistant',
          text: this.error,
          products: [],
          suggestions: [],
          action: null,
          createdAt: Date.now(),
        }
        this.messages.push(failMsg)
        return failMsg
      } finally {
        this.loading = false
      }
    },

    clear() {
      this.messages = []
      this.error = ''
    },

    setOpen(value) {
      this.open = value
      if (value && this.messages.length === 0) {
        this.fetchSuggestions()
      }
    },
  },
})
