import { createRouter, createWebHistory } from 'vue-router'

// Views
import HomeView from '../views/HomeView.vue'
import SearchView from '../views/SearchView.vue' // Added missing import
import ProductDetail from '../views/ProductDetail.vue'
import CartView from '../views/CartView.vue'
import CheckoutView from '../views/CheckoutView.vue'
import OrderHistoryView from '../views/OrderHistoryView.vue'
import SignUpView from '../views/SignUpView.vue'
import LogInView from '../views/LogInView.vue'
import ProfileView from '../views/ProfileView.vue'

const routes = [
  {
    path: '/',
    name: 'home',
    component: HomeView
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
    path: '/profile',
    name: 'Profile',
    component: ProfileView,
    meta: { requiresAuth: true }
  }
]

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes
})

router.beforeEach((to) => {
  const token = localStorage.getItem('token')
  if (to.meta.requiresAuth && !token) {
    return { path: '/log-in', query: { redirect: to.fullPath } }
  }
  if (to.meta.guestOnly && token) {
    return { path: typeof to.query.redirect === 'string' ? to.query.redirect : '/' }
  }
})

export default router