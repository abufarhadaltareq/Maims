import { defineStore } from 'pinia'
import { getProductDisplayPrice } from '../utils/pricing.js'

export const CURRENCIES = [
  { code: 'EUR', symbol: '€', country: 'PT' },
  { code: 'PKR', symbol: 'Rs', country: 'PK' },
  { code: 'USD', symbol: '$', country: 'US' },
  { code: 'SEK', symbol: 'kr', country: 'SE' },
  { code: 'BDT', symbol: '৳', country: 'BD' },
]

const readCart = () => {
  try {
    const raw = JSON.parse(localStorage.getItem('cart_items')) || []
    // Normalize legacy shapes: {product, quantity} or {product, item_quantity} or flat product rows
    return raw.map((row) => {
      if (row && row.product) {
        return {
          product: row.product,
          size: row.size || '',
          quantity: Number(row.item_quantity ?? row.quantity ?? 1) || 1,
        }
      }
      // flat legacy: product fields at top level
      const { quantity = 1, size = '', ...product } = row || {}
      return { product, size, quantity: Number(quantity) || 1 }
    }).filter((r) => r.product && r.product.id != null)
  } catch {
    return []
  }
}

export const useCartStore = defineStore('cart', {
  state: () => ({
    items: readCart(),
    // Single source of truth for currency. Default EUR to match backend/Stripe default.
    currentCurrency: localStorage.getItem('selected_currency') || 'EUR',
    lastAddedAt: 0,
  }),
  
  actions: {
    // Currency Action
    setCurrency(currency) {
      const code = (currency || 'EUR').toUpperCase()
      this.currentCurrency = code
      localStorage.setItem('selected_currency', code)
    },

    // Cart Actions
    persist() {
      localStorage.setItem('cart_items', JSON.stringify(this.items))
    },

    setQuantity(productId, size = '', quantity = 1) {
      const qty = Math.max(1, Math.min(99, Number(quantity) || 1))
      const item = this.items.find((i) => i.product.id === productId && (i.size || '') === (size || ''))
      if (item) {
        item.quantity = qty
        this.persist()
      }
      return qty
    },

    addToCart(product, selectedSize = '', quantity = 1) {
      const qty = Math.max(1, Math.min(99, Number(quantity) || 1))
      const existingItem = this.items.find(item => item.product.id === product.id && (item.size || '') === (selectedSize || ''))
      if (existingItem) {
        existingItem.quantity = Math.min(99, existingItem.quantity + qty)
        // Refresh snapshot so price/currency changes propagate
        existingItem.product = { ...existingItem.product, ...product }
      } else {
        this.items.push({ product, size: selectedSize, quantity: qty })
      }
      this.persist()
      this.lastAddedAt = Date.now()
    },

    incrementQuantity(productId, size = '') {
      const item = this.items.find(item => item.product.id === productId && (item.size || '') === (size || ''))
      if (item) {
        // Respect stock cap when known
        const cap = Number(item.product?.stock) || 99
        item.quantity = Math.min(cap, item.quantity + 1, 99)
        this.persist()
      }
    },

    decrementQuantity(productId, size = '') {
      const itemIndex = this.items.findIndex(item => item.product.id === productId && (item.size || '') === (size || ''))
      if (itemIndex !== -1) {
        const item = this.items[itemIndex]
        if ((item.quantity || 0) > 1) {
          item.quantity -= 1
        } else {
          this.items.splice(itemIndex, 1)
        }
        this.persist()
      }
    },

    removeItem(productId, size = '') {
      this.items = this.items.filter(item => !(item.product.id === productId && (item.size || '') === (size || '')))
      this.persist()
    },

    clearCart() {
      this.items = []
      localStorage.removeItem('cart_items')
    },
  },

  getters: {
    currencySymbol: (state) => {
      return (CURRENCIES.find((c) => c.code === state.currentCurrency) || {}).symbol || state.currentCurrency
    },
    cartTotalLength: (state) => {
      return state.items.reduce((total, item) => total + (item.quantity || 0), 0)
    },
    // Single reactive money helper so every view agrees on totals.
    cartPricing: (state) => {
      const currency = state.currentCurrency || 'EUR'
      let subtotal = 0
      let count = 0
      const lines = state.items.map((item) => {
        const qty = Number(item.quantity) || 0
        const unit = getProductDisplayPrice(item.product || {}, currency).numeric || 0
        const line = unit * qty
        subtotal += line
        count += qty
        return { key: `${item.product?.id}-${item.size || ''}`, unit, qty, line }
      })
      return { currency, subtotal, count, lines }
    },
  }
})