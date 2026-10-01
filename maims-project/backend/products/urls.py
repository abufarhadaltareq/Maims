from django.urls import path
from . import views
from rest_framework.authtoken.views import obtain_auth_token

urlpatterns = [
    # 🌟 NEW: This matches what HomeView.vue is now requesting!
    path('products/', views.LatestProductsList.as_view()),
    path('products/search/', views.ProductSearch.as_view()),
    
    # Keeps your existing legacy endpoints intact
    path('latest-products/', views.LatestProductsList.as_view()),
    path('categories/', views.CategoryList.as_view()),
    path('hero-slides/', views.HeroSlideList.as_view()),
    path('category-showcase/', views.CategoryShowcase.as_view()),
    path('products/category/<slug:category_slug>/', views.CategoryProducts.as_view()),
    path('products/<slug:slug>/', views.ProductDetail.as_view()),

    path('checkout/', views.checkout, name='checkout'),
    path('checkout/confirm/', views.confirm_checkout, name='confirm_checkout'),
    path('stripe-key/', views.stripe_key, name='stripe_key'),
    path('stripe-webhook/', views.stripe_webhook, name='stripe_webhook'),
    path('site-settings/', views.site_settings, name='site_settings'),
    path('orders/', views.get_orders, name='get_orders'),

    # Authentication Endpoints
    path('register/', views.register_user, name='register_user'),
    path('login/', views.login_user, name='login_user'),
    path('logout/', views.logout_user, name='logout_user'),
    path('me/', views.me, name='me'),
    path('change-password/', views.change_password, name='change_password'),
    # Legacy DRF token endpoint kept for back-compat:
    path('token-login/', obtain_auth_token, name='token_login'),
    path('profile/', views.my_profile, name='my_profile')
]