import { defineStore } from 'pinia'
import axios from 'axios'
import { useAuthStore } from './auth'

/**
 * Wishlist store — standard e-commerce behaviour.
 *
 * Rows are shaped `{ id, product }` where `id` is the SERVER wishlist row id
 * (the backend keys DELETE /wishlist/<id>/ by the row, not the product). The
 * full ProductSerializer snapshot rides along so the wishlist page renders
 * ProductCard with zero extra mapping.
 *
 * Signed-in customers: every change is mirrored to the API so the wishlist
 * follows them across devices. Guests: hearts live in localStorage (like
 * Amazon) so the heart gives instant feedback without firing an
 * IsAuthenticated API call — that would 401 and bounce the visitor to the
 * login page via the global axios interceptor. Guest hearts are merged into
 * the server wishlist on sign-in (see hydrate).
 */
const canSync = () => !!useAuthStore().token

export const useWishlistStore = defineStore('wishlist', {
  state: () => ({
    items: JSON.parse(localStorage.getItem('wishlist_items') || '[]'),
    loading: false,
    error: '',
  }),
  getters: {
    /** Number of saved items (drives the header heart badge). */
    count: (state) => state.items.length,
    /** Product ids currently saved — O(1) membership test for heart toggles. */
    savedIds: (state) => new Set(state.items.map((i) => i.product?.id ?? i.id)),
    /** Is a given product saved? Read sibling getters via `this` — `state`
        only sees actual state, so `state.savedIds` was always undefined. */
    isSaved() {
      return (productId) => this.savedIds.has(Number(productId))
    },
  },
  actions: {
    persist() {
      localStorage.setItem('wishlist_items', JSON.stringify(this.items))
    },

    /**
     * Sync with the server once the user signs in. Guest hearts accumulated
     * before sign-in are merged (POSTed up), never wiped.
     */
    async hydrate() {
      if (!canSync()) return // guest: the localStorage wishlist IS the wishlist

      this.loading = true
      this.error = ''
      try {
        const pending = this.items.filter((i) => !i.id && i.product?.id)
        const res = await axios.get('/api/v1/wishlist/')
        const rows = (res.data.results || res.data || []).map((r) => ({
          id: r.id,
          product: r.product,
        }))
        const serverIds = new Set(rows.map((r) => r.product?.id))
        for (const guest of pending) {
          if (serverIds.has(guest.product.id)) continue
          try {
            const saved = await axios.post('/api/v1/wishlist/', { product_id: guest.product.id })
            rows.push({ id: saved.data.id, product: guest.product })
          } catch {
            // Server rejected the merge (e.g. product deleted) — skip it.
          }
        }
        this.items = rows
        this.persist()
      } catch {
        // Keep local items; a failed sync must never blank the wishlist.
      } finally {
        this.loading = false
      }
    },

    /** Optimistically add a product, then mirror to the API when signed in. */
    async add(product) {
      const id = product.id
      const existing = this.items.find((i) => (i.product?.id ?? i.id) === id)
      if (existing) return existing

      // Optimistic UI first — the heart must respond instantly.
      const row = { id: null, product }
      this.items.push(row)
      this.persist()

      if (!canSync()) return row // guest wishlist: localStorage only, no 401

      try {
        const res = await axios.post('/api/v1/wishlist/', { product_id: id })
        row.id = res.data.id ?? null // server row id — required by DELETE
        this.persist()
      } catch (err) {
        if (err.response?.status === 401) return row // expired token: keep local
        // Roll back if the server rejects it.
        this.items = this.items.filter((i) => i.product?.id !== id)
        this.persist()
        throw new Error('Could not save this item.')
      }
      return row
    },

    /**
     * Remove a product. Idempotent. DELETE is keyed by the wishlist ROW id —
     * the old code sent the product id, which 404'd and made removed items
     * resurrect on every refresh.
     */
    async remove(productId) {
      const id = Number(productId)
      const row = this.items.find((i) => (i.product?.id ?? i.id) === id)
      this.items = this.items.filter((i) => (i.product?.id ?? i.id) !== id)
      this.persist()

      if (row?.id && canSync()) {
        try {
          await axios.delete(`/api/v1/wishlist/${row.id}/`)
        } catch {
          // 404 = already gone server-side; local state is correct either way.
        }
      }
    },

    /** Toggle a product: add if unsaved, remove if saved. */
    async toggle(product) {
      if (this.savedIds.has(product.id)) await this.remove(product.id)
      else await this.add(product)
    },

    /** Reset local state only — used on logout so the server copy survives. */
    clear() {
      this.items = []
      this.persist()
    },

    /** "Clear all": purge the server rows too, or they resurrect on next sync. */
    async clearAll() {
      const rows = this.items.filter((i) => i.id)
      this.items = []
      this.persist()
      if (!rows.length || !canSync()) return
      await Promise.allSettled(rows.map((r) => axios.delete(`/api/v1/wishlist/${r.id}/`)))
    },
  },
})

/** Back-compat shim so any component importing useWishlistStore still works. */
export const useWishListStore = useWishlistStore