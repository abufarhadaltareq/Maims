# 🎯 Quick Deployment Checklist

Follow these 5 simple steps to get your app live online:

## Step 1: Push to GitHub ✅

```bash
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/maims-ecommerce.git
git push -u origin main
```

**Result:** Your code is now on GitHub

---

## Step 2: Deploy Frontend (2 min) ✅

1. Go to [vercel.com](https://vercel.com)
2. Click **Import Project** → Select your GitHub repo
3. Set **Root Directory** to `frontend/`
4. Click **Deploy**
5. Add environment variable: `VITE_API_URL=YOUR_BACKEND_URL`

**Result:** Frontend live at `https://your-app.vercel.app`

---

## Step 3: Deploy Backend (5 min) ✅

### Using Railway (Recommended)

1. Go to [railway.app](https://railway.app)
2. Click **New Project** → **Deploy from GitHub repo**
3. Select your repository
4. Click **Add PostgreSQL** (Railway adds it automatically)
5. Go to **Variables** tab and add:
   - `DEBUG=False`
   - `SECRET_KEY=` (use a secure key)
   - `STRIPE_SECRET_KEY=sk_test_xxx`
   - `STRIPE_PUBLISHABLE_KEY=pk_test_xxx`
   - `ALLOWED_HOSTS=your-railway-domain.railway.app`
   - `CORS_ALLOWED_ORIGINS=https://your-vercel-frontend.vercel.app`

6. Click **Deploy**

**Result:** Backend live at `https://your-backend.railway.app`

---

## Step 4: Setup GitHub Actions (Auto-Deploy) ✅

1. Go to your GitHub repo → **Settings** → **Secrets and variables** → **Actions**
2. Add these secrets:
   - `VERCEL_TOKEN` (from [vercel.com/account/tokens](https://vercel.com/account/tokens))
   - `VERCEL_ORG_ID` (from Vercel settings)
   - `VERCEL_PROJECT_ID` (from Vercel project settings)
   - `RAILWAY_TOKEN` (from [railway.app account tokens](https://railway.app/account/tokens))

3. Now on every `git push` to main:
   - ✅ Tests run automatically
   - ✅ Frontend deploys to Vercel
   - ✅ Backend deploys to Railway

**Result:** Automatic deployment on every push!

---

## Step 5: Update Frontend API URL ✅

In Vercel Dashboard:
1. Go to **Settings** → **Environment Variables**
2. Set `VITE_API_URL` to your backend URL
3. Redeploy

**Result:** Frontend connected to backend!

---

## 🚀 You're Live!

- **Frontend:** `https://your-app.vercel.app`
- **Backend:** `https://your-backend.railway.app`
- **Admin Panel:** `https://your-backend.railway.app/admin/`

---

## Common Issues & Fixes

### ❌ "Frontend can't connect to backend"
→ Check `CORS_ALLOWED_ORIGINS` in backend environment variables

### ❌ "Database errors"
→ Railway automatically adds PostgreSQL. Make sure `DATABASE_URL` is set

### ❌ "Static files not loading"
→ Run: `python manage.py collectstatic --noinput`

### ❌ "Admin panel shows 404"
→ Add `ALLOWED_HOSTS=your-railway-domain.railway.app` to environment variables

---

## Alternative Platforms

### Backend
- **Railway** ← Recommended (easiest)
- **Render** (free tier available)
- **Heroku** (paid, but simple)

### Frontend  
- **Vercel** ← Recommended (fastest)
- **Netlify** (similar to Vercel)
- **GitHub Pages** (static only)

---

See [DEPLOYMENT.md](DEPLOYMENT.md) for detailed instructions!
