import stripe
import os
from decimal import Decimal
from django.conf import settings
from django.http import Http404
from rest_framework.views import APIView
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth.models import User
from rest_framework.authtoken.models import Token
from .models import Category, Order, OrderItem, Product, UserProfile
from .serializers import CategorySerializer, OrderSerializer, ProductSerializer, UserProfileSerializer

# 🔑 Make sure STRIPE_SECRET_KEY is added to your settings.py
stripe.api_key = settings.STRIPE_SECRET_KEY

STRIPE_PUBLISHABLE_KEY = settings.STRIPE_PUBLISHABLE_KEY


# --- 🌟 RESTORED: PRODUCT VIEWS ---

class LatestProductsList(APIView):
    """
    Handles fetching the newest items for the homepage 'New Arrivals' section.
    """
    permission_classes = [AllowAny]

    def get(self, request, format=None):
        # Grabs the 4 most recent products
        products = Product.objects.all()[0:4]
        serializer = ProductSerializer(products, many=True)
        return Response(serializer.data)


class ProductDetail(APIView):
    """
    Handles fetching data for an individual product's detail page.
    """
    permission_classes = [AllowAny]

    def get(self, request, slug, format=None):
        try:
            product = Product.objects.get(slug=slug)
            serializer = ProductSerializer(product)
            return Response(serializer.data)
        except Product.DoesNotExist:
            raise Http404


class CategoryList(APIView):
    """
    Lists all available product categories for navigation.
    """
    permission_classes = [AllowAny]

    def get(self, request, format=None):
        categories = Category.objects.all()
        serializer = CategorySerializer(categories, many=True)
        return Response(serializer.data)


class CategoryProducts(APIView):
    """
    Returns products for a selected category.
    """
    permission_classes = [AllowAny]

    def get(self, request, category_slug, format=None):
        try:
            category = Category.objects.get(slug=category_slug)
        except Category.DoesNotExist:
            raise Http404

        products = Product.objects.filter(category=category)
        serializer = ProductSerializer(products, many=True)
        return Response(serializer.data)


# --- 💳 CHECKOUT & ORDER VIEWS ---

@api_view(['POST'])
@permission_classes([AllowAny])
def checkout(request):
    data = request.data
    
    try:
        # 1. Convert total amount to cents for Stripe (e.g., 10.50 € -> 1050 cents)
        amount_in_cents = int(float(data['total_amount']) * 100)
        
        # 2. Create a PaymentIntent on Stripe with automatic card support
        intent = stripe.PaymentIntent.create(
            amount=amount_in_cents,
            currency='eur',
            automatic_payment_methods={'enabled': True},
            receipt_email=data.get('email'),
            metadata={'customer_email': data.get('email')}
        )

        order_user = request.user if request.user.is_authenticated else None

        order = Order.objects.create(
            user=order_user,
            first_name=data['first_name'],
            last_name=data['last_name'],
            email=data['email'],
            phone=data.get('phone', ''),
            address=data['address'],
            zipcode=data['zipcode'],
            place=data['place'],
            total_amount=Decimal(data['total_amount']),
            stripe_payment_intent_id=intent.id,
            is_paid=False
        )

        for item in data.get('items', []):
            product_id = item.get('product_id') or (item.get('product') or {}).get('id')
            product = Product.objects.get(id=product_id)
            OrderItem.objects.create(
                order=order,
                product=product,
                size=item.get('selectedSize') or item.get('size', ''),
                price=Decimal(item.get('price') or product.price),
                quantity=item.get('quantity', 1)
            )

        return Response({
            'client_secret': intent.client_secret,
            'order_id': order.id
        }, status=status.HTTP_201_CREATED)

    except Exception as e:
        print("Backend Checkout Error:", str(e))
        return Response(
            {'error': 'Something went wrong processing your checkout on the server.'}, 
            status=status.HTTP_400_BAD_REQUEST
        )

@api_view(['GET', 'PUT'])
@permission_classes([IsAuthenticated]) # 🌟 Only logged-in users can touch this endpoint
def my_profile(request):
    profile, created = UserProfile.objects.get_or_create(user=request.user)
    
    if request.method == 'GET':
        serializer = UserProfileSerializer(profile)
        return Response(serializer.data)
        
    elif request.method == 'PUT':
        # partial=True allows them to update just one field (like just phone) without breaking
        serializer = UserProfileSerializer(profile, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([AllowAny])
def register_user(request):
    data = request.data
    username = data.get('username')
    email = data.get('email')
    password = data.get('password')
    
    # 1. Validation check
    if not username or not email or not password:
        return Response(
            {'error': 'Please provide a username, email, and password.'}, 
            status=status.HTTP_400_BAD_REQUEST
        )
        
    # 2. Check if username or email is already taken
    if User.objects.filter(username=username).exists():
        return Response({'error': 'This username is already taken.'}, status=status.HTTP_400_BAD_REQUEST)
        
    if User.objects.filter(email=email).exists():
        return Response({'error': 'An account with this email already exists.'}, status=status.HTTP_400_BAD_REQUEST)
        
    try:
        # 3. Create the user securely (hashes the password automatically)
        user = User.objects.create_user(username=username, email=email, password=password)
        
        # 4. Generate the login token for this user
        token = Token.objects.create(user=user)
        
        return Response({
            'token': token.key,
            'username': user.username
        }, status=status.HTTP_201_CREATED)
        
    except Exception as e:
        print("Registration Error:", str(e))
        return Response({'error': 'Failed to create user.'}, status=status.HTTP_400_BAD_REQUEST)
    
# 🌟 ADD THIS NEW FUNCTION AT THE BOTTOM
@api_view(['GET'])
@permission_classes([IsAuthenticated])  # Only logged-in users can view their history
def get_orders(request):
    # Fetch only the orders that belong to the currently logged-in user, newest first
    orders = Order.objects.filter(user=request.user).order_by('-id')
    
    # Serialize the data (which now includes your full product details!)
    serializer = OrderSerializer(orders, many=True)
    
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([AllowAny])
def stripe_key(request):
    publishable_key = STRIPE_PUBLISHABLE_KEY
    if not publishable_key:
        return Response({'error': 'Stripe publishable key not configured.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    return Response({'publishableKey': publishable_key})


@api_view(['POST'])
@permission_classes([AllowAny])
def confirm_checkout(request):
    order_id = request.data.get('order_id')
    payment_intent_id = request.data.get('payment_intent_id')

    if not order_id or not payment_intent_id:
        return Response({'error': 'Missing order_id or payment_intent_id.'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        order = Order.objects.get(id=order_id, stripe_payment_intent_id=payment_intent_id)
    except Order.DoesNotExist:
        return Response({'error': 'Order not found.'}, status=status.HTTP_404_NOT_FOUND)

    try:
        intent = stripe.PaymentIntent.retrieve(payment_intent_id)
    except Exception as exc:
        return Response({'error': 'Unable to retrieve payment status.', 'details': str(exc)}, status=status.HTTP_400_BAD_REQUEST)

    if intent.status == 'succeeded':
        order.is_paid = True
        order.save()

        for item in order.items.all():
            product = item.product
            if product.stock >= item.quantity:
                product.stock = max(product.stock - item.quantity, 0)
                product.save()

        serializer = OrderSerializer(order)
        return Response({'order': serializer.data})

    return Response({'error': 'Payment has not completed.', 'status': intent.status}, status=status.HTTP_400_BAD_REQUEST)
