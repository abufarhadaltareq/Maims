import { defineStore } from 'pinia'

export const useCurrencyStore = defineStore('currency', {
  state: () => ({
    currency: localStorage.getItem('currency') || 'EUR',
    symbol: localStorage.getItem('symbol') || '€',
    country: localStorage.getItem('country') || 'PT'
  }),
  actions: {
    setRegion(country, currency, symbol) {
      this.country = country
      this.currency = currency
      this.symbol = symbol
      localStorage.setItem('country', country)
      localStorage.setItem('currency', currency)
      localStorage.setItem('symbol', symbol)
      // Optional: Refresh page or trigger a cart update
      window.location.reload() 
    }
  }
})