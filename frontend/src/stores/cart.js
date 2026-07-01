import { defineStore } from 'pinia'

export const useCartStore = defineStore('cart', {
  state: () => ({
    items: JSON.parse(localStorage.getItem('cart_items')) || [],
    // Add currency state, defaulting to 'PKR' or grabbing from storage
    currentCurrency: localStorage.getItem('selected_currency') || 'PKR',
  }),
  
  actions: {
    // Currency Action
    setCurrency(currency) {
      this.currentCurrency = currency
      localStorage.setItem('selected_currency', currency)
    },

    // Cart Actions
    addToCart(product, selectedSize = '', quantity = 1) {
      const existingItem = this.items.find(item => item.product.id === product.id && item.size === selectedSize)
      if (existingItem) {
        existingItem.quantity += quantity
      } else {
        this.items.push({ product, size: selectedSize, quantity })
      }
      localStorage.setItem('cart_items', JSON.stringify(this.items))
    },

    incrementQuantity(productId, size = '') {
      const item = this.items.find(item => item.product.id === productId && item.size === size)
      if (item) {
        item.quantity += 1
        localStorage.setItem('cart_items', JSON.stringify(this.items))
      }
    },

    decrementQuantity(productId, size = '') {
      const itemIndex = this.items.findIndex(item => item.product.id === productId && item.size === size)
      if (itemIndex !== -1) {
        const item = this.items[itemIndex]
        if (item.quantity > 1) {
          item.quantity -= 1
        } else {
          this.items.splice(itemIndex, 1)
        }
        localStorage.setItem('cart_items', JSON.stringify(this.items))
      }
    },
    
    removeItem(productId, size = '') {
      this.items = this.items.filter(item => !(item.product.id === productId && item.size === size))
      localStorage.setItem('cart_items', JSON.stringify(this.items))
    },

    clearCart() {
      this.items = []
      localStorage.removeItem('cart_items')
    }
  },
  
  getters: {
    cartTotalLength: (state) => {
      return state.items.reduce((total, item) => total + item.quantity, 0)
    }
  }
})