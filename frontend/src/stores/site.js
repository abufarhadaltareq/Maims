import { defineStore } from 'pinia'
import axios from 'axios'

/**
 * Storefront-wide settings from Admin → Site settings:
 * Facebook links, WhatsApp number/greeting, payment toggles.
 */
export const useSiteStore = defineStore('site', {
  state: () => ({
    settings: null,
    hero: null,
    loaded: false,
    heroLoaded: false,
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
    /** Configured social platforms (facebook included) as [{ key, label, url }].
        Facebook falls back to the shop tab URL so it renders exactly once
        whether the admin filled the page URL, the shop URL, or both. Blank
        platforms are skipped and appear on the storefront as soon as the
        admin connects them. */
    socialLinks: (s) => {
      const platforms = [
        ['facebook', 'Facebook', s.settings?.facebook_page_url || s.settings?.facebook_shop_url],
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

    // --- Brand color & content color settings (Admin → Site settings → Brand) ---
    brandPrimaryColor: (s) => s.settings?.brand_color || '#7C3AED',
    contentTextColor: (s) => s.settings?.content_color || '#1F2937',
    contentTextSecondary: (s) => s.settings?.content_text_secondary || '#4B5563',
    headingColor: (s) => s.settings?.heading_color || '#7C3AED',
    storeName: (s) => s.settings?.store_name || 'Maims',
    logoUrl: (s) => s.settings?.logo_url || '',
    /** Header tagline under the logo. Falls back to the legacy default. */
    tagline: (s) => s.settings?.tagline ?? 'Premium Fashion',
    footerAbout: (s) => s.settings?.footer_about || 'Curated premium fashion, delivered worldwide.',
    footerBottomNote: (s) => s.settings?.footer_bottom_note || 'Premium fashion, delivered worldwide',
    /** Scrolling top-bar messages: one per line in the admin textarea. */
    tickerMessages: (s) => {
      const raw = s.settings?.announcement_messages ?? ''
      return String(raw).split(/\r?\n/).map((m) => m.trim()).filter(Boolean)
    },
    tickerEnabled: (s) => s.settings?.announcement_enabled !== false,
    tickerSpeed: (s) => {
      const n = Number(s.settings?.announcement_speed)
      return Number.isFinite(n) && n >= 5 ? Math.min(n, 120) : 30
    },
    // --- Hero banner controls (Admin → Hero banner settings) ---
    heroEnabled: (s) => s.hero?.hero_enabled !== false,
    heroHeight: (s) => s.hero?.height_preset || 'tall',
    heroOverlay: (s) => Number(s.hero?.overlay_strength) || 45,
    heroKenburns: (s) => Number(s.hero?.kenburns_intensity) || 12,
    hero3DEnabled: (s) => s.hero?.hero_3d_enabled !== false,
    hero3DOpacity: (s) => Number(s.hero?.hero_3d_opacity) ?? 45,
    hero3DBlend: (s) => s.hero?.hero_3d_blend !== false,
    heroRotation: (s) => Number(s.hero?.rotation_seconds) || 5,
    heroTransition: (s) => Number(s.hero?.transition_ms) || 1100,
    heroAutoplay: (s) => s.hero?.autoplay !== false,
    heroAccent: (s) => s.hero?.accent_color || '#0ea5e9',
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
    async fetchHero() {
      try {
        const res = await axios.get('/api/v1/hero-banner/')
        this.hero = res.data
      } catch {
        this.hero = null
      } finally {
        this.heroLoaded = true
      }
      return this.hero
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
