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
    /** Messenger deep link (https://m.me/<username>) derived from the
        configured Facebook page URL. Empty when no page is set. */
    messengerUrl: (s) => {
      const match = (s.settings?.facebook_page_url || '')
        .match(/facebook\.com\/([^/?#]+)/i)
      return match ? `https://m.me/${match[1]}` : ''
    },
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
    stripeEnabled: (s) => s.settings?.stripe_enabled !== false,
    paypalEnabled: (s) => s.settings?.paypal_enabled !== false,
    // --- Email-marketing consent row (Admin → Customer notification settings) ---
    /** Footer sign-up form: its toggle on AND the shop can actually receive sign-ups. */
    newsletterSignupEnabled: (s) =>
      !!s.settings?.newsletter?.signup_enabled && !!s.settings?.newsletter?.accepts_signups,
    /** Checkout opt-in checkbox: its own toggle, same delivery gate. */
    newsletterCheckoutEnabled: (s) =>
      !!s.settings?.newsletter?.checkout_opt_in_enabled && !!s.settings?.newsletter?.accepts_signups,
    /** Admin-editable consent wording shown next to the checkout box. */
    newsletterConsentText: (s) =>
      s.settings?.newsletter?.consent_text ||
      'Email me about new drops, restocks and offers. Unsubscribe any time.',
    /** Box default: ticked only when the shop chose the (non-EU) opt-out strategy. */
    newsletterBoxTicked: (s) => !!s.settings?.newsletter?.box_starts_ticked,
    whatsappBaseLink: (s) => s.settings?.whatsapp_link || '',
    storeName: (s) => s.settings?.store_name || 'Maims',
    logoUrl: (s) => s.settings?.logo_url || '',
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
