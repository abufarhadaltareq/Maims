# 🚀 Deployment Guide - Maims E-Commerce Platform

This guide covers setting up auto-deployment for both frontend and backend with GitHub Actions, Vercel, Railway, and Render.

## Table of Contents

1. [GitHub Setup](#github-setup)
2. [Frontend Deployment (Vercel)](#frontend-deployment-vercel)
3. [Backend Deployment (Railway or Render)](#backend-deployment)
4. [Database Setup](#database-setup)
5. [Environment Variables](#environment-variables)
6. [Monitoring & Logs](#monitoring--logs)

---

## GitHub Setup

### 1. Create GitHub Repository

```bash
cd 'Maims app'
git remote add origin https://github.com/YOUR_USERNAME/maims-ecommerce.git
git branch -M main
git push -u origin main
```

### 2. Enable GitHub Actions

1. Go to your repository on GitHub
2. Click **Settings** → **Actions** → **General**
3. Enable "Actions" if not already enabled
4. Set **Workflow permissions** to "Read and write permissions"

---

## Frontend Deployment (Vercel)

### Step 1: Create Vercel Account

1. Go to [vercel.com](https://vercel.com)
2. Sign up with GitHub
3. Authorize Vercel to access your repositories

### Step 2: Create Vercel Project

1. Click **Add New** → **Project**
2. Select your `maims-ecommerce` repository
3. Configure:
   - **Framework Preset**: Vite
   - **Root Directory**: `frontend`
   - **Build Command**: `npm run build`
   - **Output Directory**: `dist`

### Step 3: Set Environment Variables

In Vercel Dashboard → **Settings** → **Environment Variables**:

```
VITE_API_URL=https://your-backend-domain.com
```

### Step 4: Deploy

Click **Deploy** - Vercel will build and deploy automatically!

**Your frontend will be live at:** `https://maims-ecommerce.vercel.app`

---

## Backend Deployment

Choose one: **Railway** (recommended) or **Render**

### Option A: Railway Deployment

#### Step 1: Create Railway Account

1. Go to [railway.app](https://railway.app)
2. Sign up with GitHub
3. Grant access to your repositories

#### Step 2: Deploy from GitHub

1. Click **New Project**
2. Select **Deploy from GitHub repo**
3. Choose `maims-ecommerce` repository
4. Select the `maims-project/backend` directory

#### Step 3: Add PostgreSQL Database

1. In your Railway project, click **New**
2. Select **Database** → **PostgreSQL**
3. Railway will automatically set `DATABASE_URL` environment variable

#### Step 4: Configure Environment Variables

Click **Variables** and add:

```
DEBUG=False
SECRET_KEY=your-very-secret-key-here
STRIPE_SECRET_KEY=sk_test_xxx
STRIPE_PUBLISHABLE_KEY=pk_test_xxx
ALLOWED_HOSTS=your-railway-domain.railway.app
CORS_ALLOWED_ORIGINS=https://your-vercel-frontend.vercel.app
```

#### Step 5: Set Up Auto-Deploy

Railway auto-deploys on every push to `main` branch!

**Your backend will be live at:** `https://your-railway-domain.railway.app`

---

### Option B: Render Deployment (Alternative)

#### Step 1: Create Render Account

1. Go to [render.com](https://render.com)
2. Sign up with GitHub

#### Step 2: Deploy Backend

1. Click **New +** → **Web Service**
2. Connect your GitHub repository
3. Configure:
   - **Name**: `maims-backend`
   - **Environment**: Python 3.11
   - **Build Command**: `pip install -r requirements.txt && python manage.py collectstatic --noinput`
   - **Start Command**: `gunicorn core.wsgi`
   - **Region**: Choose closest to you

#### Step 3: Add PostgreSQL Database

1. Click **New +** → **PostgreSQL**
2. Create database with default settings
3. Render will automatically set `DATABASE_URL`

#### Step 4: Set Environment Variables

In the Web Service settings → **Environment**:

```
DEBUG=False
SECRET_KEY=your-secret-key
STRIPE_SECRET_KEY=sk_test_xxx
STRIPE_PUBLISHABLE_KEY=pk_test_xxx
ALLOWED_HOSTS=your-render-domain.onrender.com
CORS_ALLOWED_ORIGINS=https://your-vercel-frontend.vercel.app
```

#### Step 5: Deploy

Click **Deploy** - Render will build and deploy!

**Your backend will be live at:** `https://maims-backend.onrender.com`

---

## Database Setup

### PostgreSQL Connection String

Once database is created, you should have a connection string like:

```
postgresql://username:password@host:5432/database_name
```

Most platforms (Railway, Render) set this as `DATABASE_URL` automatically.

### Running Migrations in Production

After deploying, run migrations manually if needed:

```bash
# For Railway
railway run python manage.py migrate

# For Render
render exec python manage.py migrate
```

Or configure auto-migration in Procfile (already included):

```
release: python manage.py migrate
```

---

## Environment Variables

### Backend (.env)

Copy `.env.example` to `.env` and fill in:

```bash
# Core
DEBUG=False
SECRET_KEY=generate-secure-key-here

# Database (optional, defaults to SQLite)
DATABASE_URL=postgresql://user:pass@host/db

# Stripe
STRIPE_SECRET_KEY=sk_test_your_key
STRIPE_PUBLISHABLE_KEY=pk_test_your_key

# CORS (add your frontend domain)
CORS_ALLOWED_ORIGINS=http://localhost:5173,https://your-frontend-domain.com

# Allowed Hosts
ALLOWED_HOSTS=localhost,127.0.0.1,your-backend-domain.com
```

### Generate Secret Key

```python
from django.core.management.utils import get_random_secret_key
print(get_random_secret_key())
```

### Frontend (.env)

```bash
VITE_API_URL=https://your-backend-domain.com
```

---

## CI/CD with GitHub Actions

The `.github/workflows/ci-cd.yml` file automatically:

1. **Runs tests** on every push
2. **Builds** frontend and backend
3. **Deploys to Vercel** (frontend) on main push
4. **Deploys to Railway** (backend) on main push

### Required Secrets for GitHub Actions

1. Go to Repository → **Settings** → **Secrets and variables** → **Actions**
2. Add these secrets:

```
VERCEL_TOKEN          # Get from Vercel Settings
VERCEL_ORG_ID         # Get from Vercel Account Settings
VERCEL_PROJECT_ID     # Get from Vercel Project Settings
RAILWAY_TOKEN         # Get from Railway Account Settings
```

### Get Vercel Credentials

1. Go to [vercel.com/account/tokens](https://vercel.com/account/tokens)
2. Create new token
3. Copy and paste in GitHub Secrets

### Get Railway Token

1. Go to [railway.app/account/tokens](https://railway.app/account/tokens)
2. Create new token
3. Copy and paste in GitHub Secrets

---

## Monitoring & Logs

### View Deployment Logs

**Vercel:**
- Dashboard → **Deployments** → Click deployment → **Logs**

**Railway:**
- Dashboard → **Logs** tab

**Render:**
- Dashboard → **Logs** tab

### Monitor Uptime

- **Vercel Analytics**: Built-in monitoring
- **Railway Status**: Dashboard shows service health
- **Render Logs**: Check error logs for issues

---

## Troubleshooting

### Frontend not connecting to backend
- Check `VITE_API_URL` environment variable
- Ensure backend domain is in `CORS_ALLOWED_ORIGINS`
- Check browser console for CORS errors

### Migrations failing
- SSH into server and run: `python manage.py migrate`
- Check database connection string

### Static files not loading
- Run: `python manage.py collectstatic --noinput`
- Check `STATIC_ROOT` in Django settings

### 500 errors
- Check backend logs for traceback
- Ensure all environment variables are set
- Verify database connection

---

## Local Development with Docker

For local testing that mimics production:

```bash
docker-compose up
```

This starts:
- PostgreSQL database on port 5432
- Django backend on port 8000
- Vite frontend on port 5173

---

## Next Steps

1. ✅ Push to GitHub
2. ✅ Deploy frontend to Vercel
3. ✅ Deploy backend to Railway/Render
4. ✅ Add custom domain (optional)
5. ✅ Set up monitoring

Your e-commerce platform is now live! 🎉
