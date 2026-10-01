import { defineStore } from 'pinia'
import axios from 'axios'

/**
 * Storefront-wide settings from Admin → Site settings:
 * Facebook links, WhatsApp number/greeting, payment toggles.
 */
export const useSiteStore = defineStore('site', {
  state: () => ({
    settings: null,
    loaded: false,
  }),
  getters: {
    facebookPageUrl: (s) => s.settings?.facebook_page_url || '',
    facebookShopUrl: (s) => s.settings?.facebook_shop_url || '',
    instagramUrl: (s) => s.settings?.instagram_url || '',
    tiktokUrl: (s) => s.settings?.tiktok_url || '',
    twitterUrl: (s) => s.settings?.twitter_url || '',
    youtubeUrl: (s) => s.settings?.youtube_url || '',
    linkedinUrl: (s) => s.settings?.linkedin_url || '',
    /** Configured social platforms (facebook included) as [{ key, label, url }]. */
    socialLinks: (s) => {
      const platforms = [
        ['facebook', 'Facebook', s.settings?.facebook_page_url],
        ['instagram', 'Instagram', s.settings?.instagram_url],
        ['tiktok', 'TikTok', s.settings?.tiktok_url],
        ['twitter', 'X', s.settings?.twitter_url],
        ['youtube', 'YouTube', s.settings?.youtube_url],
        ['linkedin', 'LinkedIn', s.settings?.linkedin_url],
      ]
      return platforms
        .filter(([, , url]) => !!url)
        .map(([key, label, url]) => ({ key, label, url }))
    },
    whatsappNumber: (s) => s.settings?.whatsapp_number || '',
    whatsappEnabled: (s) => !!(s.settings?.whatsapp_enabled && s.settings?.whatsapp_number),
    codEnabled: (s) => s.settings?.cod_enabled !== false,
    stripeEnabled: (s) => s.settings?.stripe_enabled !== false,
    whatsappBaseLink: (s) => s.settings?.whatsapp_link || '',
  },
  actions: {
    async fetchSettings() {
      try {
        const res = await axios.get('/api/v1/site-settings/')
        this.settings = res.data
      } catch {
        this.settings = null
      } finally {
        this.loaded = true
      }
      return this.settings
    },
    /** Build a wa.me link with the cart contents prefilled. */
    whatsappOrderLink(greeting, lines, totalLine) {
      const num = (this.settings?.whatsapp_number || '').replace(/\D/g, '')
      if (!num) return ''
      const head = greeting || this.settings?.whatsapp_greeting || 'Hello! I want to order:'
      const text = [head, ...lines, totalLine].filter(Boolean).join('\n')
      return `https://wa.me/${num}?text=${encodeURIComponent(text)}`
    },
  },
})
