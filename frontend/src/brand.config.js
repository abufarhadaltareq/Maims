export const BRAND_CONFIG = {
  name: "Maims",
  domain: "maims.eu",
  currencySymbol: "€",
  supportEmail: "shop@maims.eu",

  // Logo tagline fallback (header/footer wordmark). The live value comes from
  // Admin → Site settings → Brand & header → Tagline; empty hides the line.
  tagline: "Premium Fashion",

  apiBaseUrl: "",

  // Fallback hero content — used only until admin HeroSlides load
  // (or if the API is unreachable). Manage real slides in Admin → Hero slides.
  heroBannerTitle: "Elevate Your Everyday Style",
  heroBannerSubtitle: "Discover curated premium clothing collections tailored just for you.",

  // Fallback rotating images (premium fashion)
  heroImages: [
    "https://images.unsplash.com/photo-1441986300917-64674bd600d8?q=80&w=1600&auto=format&fit=crop", // Main Shop
    "https://images.unsplash.com/photo-1490481651871-ab68de25d43d?q=80&w=1600&auto=format&fit=crop", // Luxury Fabrics
    "https://images.unsplash.com/photo-1469334031218-e382a71b716b?q=80&w=1600&auto=format&fit=crop"  // Elegant Fits
  ],

  // Promo badge shown in the category nav (premium-fashion accent)
  promoBadge: "New Season Drop",
  promoBadgeBg: "bg-rose-600",

  // Category navigation labels (top nav, premium fashion style)
  navCategories: [
    { name: "Women", slug: "women" },
    { name: "Men", slug: "men" },
    { name: "Kids", slug: "kids" },
    { name: "Home Décor", slug: "home-decor" },
    { name: "Jewellery", slug: "jewellery" }
  ],

  // Category pill chips shown below the main nav (premium-fashion accents)
  categoryPills: [
    { label: "New Arrivals", href: "/new-arrivals", accent: true },
    { label: "Best Seller", href: "/category/best-seller" },
    { label: "Summer Edit", href: "/category/summer-edit" },
    { label: "Plus Size", href: "/category/plus-size" },
    { label: "Dresses", href: "/category/dresses" },
    { label: "Tops", href: "/category/tops" },
    { label: "Outerwear", href: "/category/outerwear" },
    { label: "Accessories", href: "/category/accessories" },
    { label: "Sale", href: "/category/sale" },
    { label: "Gift Cards", href: "/category/gift-cards" }
  ],

  enableTrackingPage: true,
  enableStockAlerts: true,

  // WhatsApp top-bar CTA
  whatsappCta: "For customized product: WhatsApp Now",
  whatsappCtaUrl: "https://wa.me/"
}