export const BRAND_CONFIG = {
  name: "Maims",
  domain: "maims.com",
  currencySymbol: "€",
  supportEmail: "shop@maims.com",

  // Logo tagline (shown under the wordmark) and the top announcement strip.
  // Set announcement to "" to hide the top bar entirely.
  tagline: "Premium Fashion",
  announcement: "✦ Welcome to Maims — premium fashion, delivered worldwide",

  apiBaseUrl: "",

  // Fallback hero content — used only until admin HeroSlides load
  // (or if the API is unreachable). Manage real slides in Admin → Hero slides.
  heroBannerTitle: "Elevate Your Everyday Style",
  heroBannerSubtitle: "Discover curated premium clothing collections tailored just for you.",

  // Fallback rotating images (same as before)
  heroImages: [
    "https://images.unsplash.com/photo-1441986300917-64674bd600d8?q=80&w=1200&auto=format&fit=crop", // Main Shop
    "https://images.unsplash.com/photo-1490481651871-ab68de25d43d?q=80&w=1200&auto=format&fit=crop", // Luxury Fabrics
    "https://images.unsplash.com/photo-1469334031218-e382a71b716b?q=80&w=1200&auto=format&fit=crop"  // Elegant Fits
  ],

  enableTrackingPage: true,
  enableStockAlerts: true
}