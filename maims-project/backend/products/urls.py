from django.urls import path
from . import views
from rest_framework.authtoken.views import obtain_auth_token

urlpatterns = [
    # This will be the endpoint for your homepage to get the newest items
    path('latest-products/', views.LatestProductsList.as_view()),
    path('categories/', views.CategoryList.as_view()),
    path('products/category/<slug:category_slug>/', views.CategoryProducts.as_view()),
    
    # This will be the endpoint for an individual product's detail page
    path('products/<slug:slug>/', views.ProductDetail.as_view()),

    path('checkout/', views.checkout, name='checkout'),
    path('checkout/confirm/', views.confirm_checkout, name='confirm_checkout'),
    path('stripe-key/', views.stripe_key, name='stripe_key'),

    # 🌟 UPDATED THIS LINE: Changed get_user_orders to get_orders
    path('orders/', views.get_orders, name='get_orders'),

    # 🌟 NEW: Authentication Endpoints
    path('register/', views.register_user, name='register_user'),
    path('login/', obtain_auth_token, name='login_token'), 
    
    path('profile/', views.my_profile, name='my_profile')
]