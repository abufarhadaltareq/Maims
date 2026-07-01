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
    component: OrderHistoryView
  },
  {
    path: '/sign-up',
    name: 'SignUp',
    component: SignUpView
  },
  {
    path: '/log-in',
    name: 'LogIn',
    component: LogInView
  },
  {
    path: '/profile',
    name: 'Profile',
    component: ProfileView
  }
]

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes
})

export default router