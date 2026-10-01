export const RATES_TO_USD = {
  SEK: 0.095,
  PKR: 0.0036,
  EUR: 1.08,
  BDT: 0.0085,
  USD: 1.0,
}

export const CURRENCY_SYMBOLS = {
  EUR: '€',
  USD: '$',
  PKR: 'Rs',
  SEK: 'kr',
  BDT: '৳',
}

/**
 * Resolve a display price for a product (or nested cart item product)
 * Priority: exact currency in prices[] -> convert from first prices[] entry -> product.price fallback.
 * Returns { numeric: Number, string: "12.34 EUR" }
 */
export function getProductDisplayPrice(product = {}, currency = 'EUR') {
  const selected = (currency || 'EUR').toUpperCase()

  if (product.prices && Array.isArray(product.prices) && product.prices.length > 0) {
    const exact = product.prices.find((p) => p.currency === selected)
    if (exact) {
      const n = Number(exact.price)
      return { numeric: n, string: `${n.toFixed(2)} ${selected}` }
    }
    const backup = product.prices[0]
    if (backup) {
      const basePrice = Number(backup.price)
      const baseCurrency = backup.currency
      const rateInUSD = RATES_TO_USD[baseCurrency] || 1.0
      const targetRate = RATES_TO_USD[selected] || 1.0
      // Same (inverted) formula used across views: convert via USD index.
      const converted = (basePrice * rateInUSD) / targetRate
      return { numeric: converted, string: `${converted.toFixed(2)} ${selected}` }
    }
  }

  const fallback = Number(product.price || 0)
  return { numeric: fallback, string: `${fallback.toFixed(2)} ${selected}` }
}

export function formatProductPrice(product = {}, currency = 'EUR') {
  return getProductDisplayPrice(product, currency).string
}
