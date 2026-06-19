import { createRouter, createWebHistory } from 'vue-router'
import HomeView from '../views/HomeView.vue'
import ProductDetail from '../views/ProductDetail.vue' // 🌟 This matches your actual filename
import CartView from '../views/CartView.vue'
import CheckoutView from '../views/CheckoutView.vue'
import OrderHistoryView from '../views/OrderHistoryView.vue'
import SignUpView from '../views/SignUpView.vue'
import LogInView from '../views/LogInView.vue'
import ProfileView from '../views/ProfileView.vue' // 🌟 Add this import at the top

const routes = [
  {
    path: '/',
    name: 'home',
    component: HomeView
  },
  {
    // 🌟 Unified: This matches the product.slug strings sent from your HomeView links
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
    component: ProfileView,
    // Optional: Add a meta tag here if you have navigation guards set up for logged-in users
  }
]

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes
})

export default router