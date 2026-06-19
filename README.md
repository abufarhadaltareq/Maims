# Maims E-Commerce Platform

A modern, full-stack e-commerce application built with Vue 3 + Vite frontend and Django REST Framework backend with Stripe payments integration.

## Features

- 🛍️ Product catalog with categories, sizes, and stock availability
- 🎨 Beautiful UI with 3D effects and animations
- 💳 Secure Stripe payment integration
- 📱 Fully responsive mobile design
- 🔐 User authentication and profiles
- 📦 Order tracking and history
- 🏪 Admin panel for product & category management
- 🖼️ Multiple product images and media support

## Project Structure

```
├── frontend/                 # Vue 3 + Vite frontend
│   ├── src/
│   │   ├── components/      # Reusable Vue components
│   │   ├── views/           # Page views (Home, Product, Cart, Checkout, etc.)
│   │   ├── router/          # Vue Router configuration
│   │   ├── stores/          # Pinia store (cart state)
│   │   ├── assets/          # Images and styles
│   │   └── App.vue          # Main app component
│   └── package.json         # Frontend dependencies
│
└── maims-project/
    └── backend/             # Django REST Framework backend
        ├── core/            # Django project settings
        ├── products/        # Products, orders, categories app
        ├── manage.py        # Django management script
        └── db.sqlite3       # Database (SQLite / PostgreSQL)
```

## Quick Start

### Backend Setup

```bash
cd maims-project/backend

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run migrations
python3 manage.py migrate

# Create superuser (admin)
python3 manage.py createsuperuser

# Start development server
python3 manage.py runserver
```

Backend runs on: `http://localhost:8000`

### Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

Frontend runs on: `http://localhost:5173`

## API Endpoints

### Products
- `GET /api/v1/latest-products/` - Get newest products
- `GET /api/v1/products/<slug>/` - Get product details
- `GET /api/v1/categories/` - Get all categories
- `GET /api/v1/products/category/<category_slug>/` - Get products by category

### Orders & Checkout
- `POST /api/v1/checkout/` - Create checkout order
- `POST /api/v1/checkout/confirm/` - Confirm payment with Stripe
- `GET /api/v1/orders/` - Get user orders
- `GET /api/v1/stripe-key/` - Get Stripe publishable key

### Authentication
- `POST /api/v1/register/` - Register new user
- `POST /api/v1/login/` - Login and get auth token
- `GET /api/v1/profile/` - Get user profile (requires auth)

## Payment Integration

This project uses **Stripe** for payments. To enable:

1. Get API keys from [Stripe Dashboard](https://dashboard.stripe.com)
2. Add to Django `settings.py`:
   ```python
   STRIPE_SECRET_KEY = 'your_secret_key'
   STRIPE_PUBLISHABLE_KEY = 'your_publishable_key'
   ```
3. The frontend automatically loads the Stripe key from the backend

## Environment Variables

### Backend (.env in maims-project/backend/)
```
DEBUG=True
SECRET_KEY=your_secret_key
STRIPE_SECRET_KEY=your_stripe_secret
STRIPE_PUBLISHABLE_KEY=your_stripe_publishable
ALLOWED_HOSTS=localhost,127.0.0.1
```

### Frontend (.env in frontend/)
```
VITE_API_URL=http://localhost:8000
```

## Deployment

### Frontend Deployment
- Deploy to **Vercel**, **Netlify**, or **GitHub Pages**
- Build: `npm run build`
- Output: `dist/` folder

### Backend Deployment
- Deploy to **Heroku**, **Railway**, **Render**, or **DigitalOcean**
- Requirements: Python 3.9+, PostgreSQL recommended
- See deployment guides in documentation

## Technologies Used

**Frontend:**
- Vue 3 with Composition API
- Vite (fast build tool)
- Pinia (state management)
- Axios (HTTP client)
- TailwindCSS (styling)
- Stripe JS SDK

**Backend:**
- Django 4.x
- Django REST Framework
- Token Authentication
- Stripe Python SDK
- SQLite / PostgreSQL

## License

MIT License - Feel free to use for your projects!

## Support

For issues or questions, check the documentation or create an issue on GitHub.
