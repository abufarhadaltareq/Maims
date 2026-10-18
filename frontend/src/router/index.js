import { createRouter, createWebHistory } from 'vue-router'

// Every route is loaded on demand. These views are large (the home page pulls in
// the Three.js hero, the checkout pulls in Stripe.js) and statically importing
// them put the entire storefront in the entry chunk, so a visitor who only wanted
// the login page still downloaded Three.js.
const HomeView = () => import('../views/HomeView.vue')
const SearchView = () => import('../views/SearchView.vue')
const ProductDetail = () => import('../views/ProductDetail.vue')
const CartView = () => import('../views/CartView.vue')
const CheckoutView = () => import('../views/CheckoutView.vue')
const WishlistView = () => import('../views/WishlistView.vue')
const OrderHistoryView = () => import('../views/OrderHistoryView.vue')
const SignUpView = () => import('../views/SignUpView.vue')
const LogInView = () => import('../views/LogInView.vue')
const ProfileView = () => import('../views/ProfileView.vue')
const NotFoundView = () => import('../views/NotFoundView.vue')

const routes = [
  {
    path: '/',
    name: 'home',
    component: HomeView
  },
  {
    // Terms, privacy and licence. Linked from the footer; the hash
    // (/legal#legal-terms) opens the matching tab.
    path: '/legal',
    name: 'legal',
    component: () => import('../views/LegalView.vue')
  },
  {
    path: '/search',
    name: 'search',
    component: SearchView
  },
  {
    path: '/products/:slug',
    name: 'product-detail',
    component: ProductDetail
  },
  {
    path: '/category/:category_slug',
    name: 'category',
    component: HomeView
  },
  {
    path: '/new-arrivals',
    name: 'new-arrivals',
    component: () => import('../views/NewArrivalsView.vue')
  },
  {
    path: '/cart',
    name: 'cart',
    component: CartView
  },
  {
    path: '/wishlist',
    name: 'wishlist',
    component: WishlistView
  },
  {
    path: '/checkout',
    name: 'checkout',
    component: CheckoutView
  },
  {
    path: '/order-history',
    name: 'order-history',
    component: OrderHistoryView,
    meta: { requiresAuth: true }
  },
  {
    path: '/sign-up',
    name: 'SignUp',
    component: SignUpView,
    meta: { guestOnly: true }
  },
  {
    path: '/log-in',
    name: 'LogIn',
    component: LogInView,
    meta: { guestOnly: true }
  },
  {
    path: '/forgot-password',
    name: 'ForgotPassword',
    component: () => import('../views/ForgotPasswordView.vue'),
    meta: { guestOnly: true }
  },
  {
    path: '/reset-password',
    name: 'ResetPassword',
    component: () => import('../views/ResetPasswordView.vue'),
    meta: { guestOnly: true }
  },
  {
    path: '/profile',
    name: 'Profile',
    component: ProfileView,
    meta: { requiresAuth: true }
  },
  {
    // Without a catch-all, an unknown URL matched no route and Vue Router left
    // <RouterView> empty: a blank page with no way back into the shop. This also
    // catches the SEO cost of soft-404s for removed product slugs.
    path: '/:pathMatch(.*)*',
    name: 'not-found',
    component: NotFoundView
  }
]

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes,
  scrollBehavior(to, from, savedPosition) {
    if (savedPosition) return savedPosition
    // Footer legal links point at /#legal-<doc>; the block itself is #legal.
    if (to.hash) {
      const el = to.hash.startsWith('#legal-') ? '#legal' : to.hash
      return { el, top: 80, behavior: 'smooth' }
    }
    return { top: 0 }
  }
})

router.beforeEach((to) => {
  const token = localStorage.getItem('token')
  if (to.meta.requiresAuth && !token) {
    return { path: '/log-in', query: { redirect: to.fullPath } }
  }
  if (to.meta.guestOnly && token) {
    // `?redirect=` can arrive as an array when a URL repeats the parameter, so
    // only follow it when it is a single string. Never follow a protocol-relative
    // or absolute URL: that would turn the login page into an open redirect.
    const target = to.query.redirect
    if (typeof target === 'string' && target.startsWith('/') && !target.startsWith('//')) {
      return { path: target }
    }
    return { path: '/' }
  }
})

export default router
