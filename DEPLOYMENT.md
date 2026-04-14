# Render Deployment Guide

This guide explains how to deploy the Midcenturist API to Render using the provided configuration and database credentials.

## Your Render Database Info

- **Host (Internal)**: `dpg-d7ev761kh4rs73damol0-a`
- **Host (External)**: `dpg-d7ev761kh4rs73damol0-a.oregon-postgres.render.com`
- **Port**: `5432`
- **Database**: `midcenturist_prod`
- **Username**: `midcenturist_prod_user`
- **Password**: `EQZu6PjqlLkBwfmERaEGF8GOQFM6XJgJ`

### Connection URLs

**Internal** (for services on Render):
```
postgresql://midcenturist_prod_user:EQZu6PjqlLkBwfmERaEGF8GOQFM6XJgJ@dpg-d7ev761kh4rs73damol0-a/midcenturist_prod
```

**External** (for local development):
```
postgresql://midcenturist_prod_user:EQZu6PjqlLkBwfmERaEGF8GOQFM6XJgJ@dpg-d7ev761kh4rs73damol0-a.oregon-postgres.render.com/midcenturist_prod
```

---

## Before Pushing to GitHub

### 1. Secure Your Secrets

Never commit sensitive data! The `.env` file is already in `.gitignore`.

**Generate secure keys for production:**
```bash
python -c "import secrets; print(secrets.token_hex(32))"
# Run this twice and save the outputs
```

### 2. Test Locally with Render Database (Optional)

To test against the actual Render database before deployment:

```bash
# Update .env
FLASK_ENV=development
DATABASE_URL=postgresql://midcenturist_prod_user:EQZu6PjqlLkBwfmERaEGF8GOQFM6XJgJ@dpg-d7ev761kh4rs73damol0-a.oregon-postgres.render.com/midcenturist_prod

# Activate venv
source venv/bin/activate  # or: venv\Scripts\activate (Windows)

# Run migrations
flask db upgrade

# Seed sample data
python seed.py

# Test API
python run.py
# Visit: http://localhost:5000/api/health
```

### 3. Test with Local PostgreSQL (Recommended for Dev)

```bash
# Create local database
createdb midcenturist_dev

# Update .env
FLASK_ENV=development
DATABASE_URL=postgresql://postgres:postgres@localhost/midcenturist_dev

# Run migrations
flask db upgrade

# Seed sample data
python seed.py

# Test API
python run.py
```

---

## Deploying to Render

### Step 1: Prepare Repository

```bash
# Initialize git
git init

# Add all files
git add .

# Commit
git commit -m "Initial Flask API implementation with seed data and Render config"

# Push to GitHub
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/midcenturist-api.git
git push -u origin main
```

### Step 2: Create Web Service on Render

1. Go to [render.com](https://render.com)
2. Click **"New +"** → Choose **"Web Service"**
3. **Connect your GitHub repo** (authorize Render if needed)
4. Select `midcenturist-api` repository
5. **Configuration:**
   - **Name**: `midcenturist-api`
   - **Environment**: `Python 3`
   - **Region**: `Oregon` (matches your database)
   - **Branch**: `main`
   - **Build Command**: `pip install -r requirements.txt` (auto-detected)
   - **Start Command**: `gunicorn -w 4 -b 0.0.0.0:8000 --timeout 600 wsgi:app`
   - **Plan**: `Free` (can upgrade to Starter $7/mo)

6. **Add Environment Variables** (click "Environment" tab):
   ```
   FLASK_ENV=production
   FLASK_APP=wsgi.py
   SECRET_KEY=<your-generated-key-1>
   ADMIN_JWT_SECRET=<your-generated-key-2>
   DATABASE_URL=postgresql://midcenturist_prod_user:EQZu6PjqlLkBwfmERaEGF8GOQFM6XJgJ@dpg-d7ev761kh4rs73damol0-a/midcenturist_prod
   ALLOWED_ORIGINS=https://yourdomain.com,https://www.yourdomain.com,http://localhost:3000
   FROM_EMAIL=noreply@midcenturist.co.za
   # Add others as needed
   ```

7. Click **"Create Web Service"**

**Wait 2-5 minutes for deployment**

### Step 3: Initialize Database on Render

Once deployed:

1. Go to your **Web Service Dashboard**
2. Click **"Shell"** button (top right)
3. Run migrations:
   ```bash
   flask db upgrade
   ```

4. Seed sample data:
   ```bash
   python seed.py
   ```

5. Test the API:
   ```bash
   curl https://your-service-xxxx.onrender.com/api/health
   ```

---

## Test Endpoints After Deployment

### Health Check
```bash
curl https://your-service-xxxx.onrender.com/api/health
# Expected: {"status": "ok", "env": "production"}
```

### List Products
```bash
curl https://your-service-xxxx.onrender.com/api/products?limit=5
```

### Get Categories
```bash
curl https://your-service-xxxx.onrender.com/api/categories
```

### Create a Cart
```bash
curl -X POST https://your-service-xxxx.onrender.com/api/cart \
  -H "Content-Type: application/json"
```

---

## Files Included

### `seed.py`
Seeds the database with sample data:
- 3 categories (Furniture, Lighting, Decor)
- 3 collections (New In, Summer Sale, Scandinavian)
- 6 sample products with variants and images
- 3 sample reviews
- 3 sample subscribers

**Usage:**
```bash
python seed.py
```

**Run in Render Shell:**
- Dashboard → Web Service → Shell
- `python seed.py`

### `render.yaml`
Render deployment configuration. Allows one-click deployment without manual setup.

**To use:**
1. Add `render.yaml` to root of your repository
2. Go to [render.com/dashboard](https://render.com/dashboard)
3. Click **"New +"** → **"Web Service"** → **"Deploy from Git"**
4. Render auto-detects `render.yaml` and applies all settings

### `.env`
Local environment variables. Already in `.gitignore` (won't commit).

**To test locally:**
```bash
cp .env.local .env  # or create your own
# Edit .env with your variables
python run.py
```

---

## Payment Gateway Status

⚠️ **Payment endpoints are currently disabled**

The following are commented out in the code:
- `POST /api/payments/payfast/initiate`
- `POST /api/payments/payfast/webhook`
- `POST /api/payments/yoco/initiate`

**To re-enable once client decides:**
1. Edit `app/__init__.py`
2. Uncomment the payments import
3. Uncomment the payment blueprint registration
4. Add PayFast/Yoco credentials to `.env`
5. Deploy: `git push origin main`

---

## Monitoring & Maintenance

### View Logs
```bash
# In Render Dashboard:
1. Go to Web Service
2. Click "Logs" tab
3. Real-time logs appear
```

### Check Database Connection
```bash
# In Render Shell:
python
>>> from app import create_app
>>> app = create_app('production')
>>> from app.extensions import db
>>> with app.app_context():
>>>     result = db.session.execute("SELECT 1")
>>>     print(result.fetchall())
```

### Database Size
```sql
SELECT pg_size_pretty(pg_database_size('midcenturist_prod'));
```

---

## Troubleshooting

### "Build failed"
Check Logs tab. Common issues:
- Missing dependency in `requirements.txt`
- Syntax error in Python files
- Incompatible Python version

**Fix:** Add missing package to `requirements.txt`, commit, and push.

### "ModuleNotFoundError: No module named 'app'"
- Ensure `wsgi.py` is in **root** directory
- Start command should be `gunicorn -w 4 -b 0.0.0.0:8000 wsgi:app`

### "Database connection error"
- Verify `DATABASE_URL` environment variable is set
- Check it starts with `postgresql://`
- Confirm password is correct

### "CORS errors from frontend"
- Add frontend URL to `ALLOWED_ORIGINS` environment variable
- Example: `https://midcenturist.co.za,http://localhost:3000`

### Service keeps restarting
Check logs for Python errors. Common causes:
- Missing environment variables
- Database migrations failed
- Import errors

**Fix in Shell:**
```bash
flask db migrate
flask db upgrade
python seed.py
```

---

## Next Steps

1. ✅ Generated `seed.py` — run to populate test data
2. ✅ Created `render.yaml` — auto-deployment config
3. **Push to GitHub** — `git push origin main`
4. **Create Web Service on Render** — link your repo
5. **Run migrations & seed** — in Render Shell
6. **Test endpoints** — confirm API is working
7. **Connect frontend** — point to your Render domain
8. **Add real images** — upload products to Cloudinary
9. **Enable payment** — once client decides
10. **Set up monitoring** — add error tracking (Sentry, etc.)

---

## Contact & Support

For issues:
- Check logs in Render Dashboard
- Review this guide's troubleshooting section
- Read Flask/SQLAlchemy documentation
- Contact Render support for infrastructure issues

---

**Last Updated**: 2026-04-14
**API Status**: ✅ Ready for testing
**Database**: ✅ PostgreSQL on Render
**Payments**: ⚠️ Disabled (awaiting client decision)
