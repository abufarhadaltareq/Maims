import { defineStore } from 'pinia'
import { useCartStore } from './cart'

/**
 * @deprecated Currency lives in useCartStore (cart.js) as the single source of truth.
 * This shim keeps old imports working without a page reload.
 */
export const useCurrencyStore = defineStore('currency', {
  state: () => ({
    currency: localStorage.getItem('selected_currency') || 'EUR',
    symbol: localStorage.getItem('symbol') || '€',
    country: localStorage.getItem('country') || 'PT'
  }),
  actions: {
    setRegion(country, currency, symbol) {
      const cart = useCartStore()
      cart.setCurrency(currency)
      this.country = country
      this.currency = cart.currentCurrency
      this.symbol = symbol
      localStorage.setItem('country', country)
      localStorage.setItem('currency', this.currency)
      localStorage.setItem('symbol', symbol)
      // No reload: cart store is reactive, prices recompute automatically.
    }
  }
})