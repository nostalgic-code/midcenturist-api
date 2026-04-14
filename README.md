# Midcenturist API

Flask REST API for the Midcenturist vintage furniture e-commerce platform.

## Project Structure

```
midcenturist-api/
├── app/
│   ├── __init__.py           # App factory
│   ├── extensions.py         # Flask extensions (db, migrate, cors, limiter, talisman)
│   ├── models/
│   │   └── __init__.py       # All SQLAlchemy models
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── products.py       # Public product endpoints
│   │   ├── categories.py     # Public category & collection endpoints
│   │   ├── cart.py           # Shopping cart endpoints
│   │   ├── orders.py         # Order creation & public status
│   │   ├── payments.py       # PayFast & Yoco payment processing
│   │   ├── newsletter.py     # Newsletter & reviews endpoints
│   │   └── admin/
│   │       ├── __init__.py
│   │       ├── products.py   # Admin product management
│   │       └── orders.py     # Admin orders, categories, Instagram, reviews
│   └── utils/
│       ├── __init__.py
│       ├── security.py       # JWT auth, PayFast signature verification
│       ├── validators.py     # Input validation
│       └── email.py          # Email utilities (stub)
├── config.py                 # App configuration classes
├── wsgi.py                   # Production entry point (Gunicorn)
├── run.py                    # Development entry point
├── requirements.txt          # Python dependencies
└── .env.example              # Environment variable template
```

## Features

### Public API

**Products**
- `GET /api/products` — List live products with filters (category, collection, featured, badge)
- `GET /api/products/search?q=query` — Full-text search
- `GET /api/products/:slug` — Product detail with reviews

**Categories & Collections**
- `GET /api/categories` — Category tree with product counts
- `GET /api/categories/:slug/products` — Products in category
- `GET /api/collections` — Active collections
- `GET /api/collections/:slug/products` — Products in collection

**Shopping Cart** (session-based, 7-day TTL)
- `POST /api/cart` — Create new cart
- `GET /api/cart/:sessionId` — Get cart contents
- `POST /api/cart/:sessionId/items` — Add product variant
- `PUT /api/cart/:sessionId/items/:itemId` — Update quantity
- `DELETE /api/cart/:sessionId` — Clear cart

**Orders** (guest checkout)
- `POST /api/orders` — Create order from cart
- `GET /api/orders/:id` — Get order status (public view)

**Payments**
- `POST /api/payments/payfast/initiate` — Start PayFast checkout
- `POST /api/payments/payfast/webhook` — PayFast ITN webhook
- `POST /api/payments/yoco/initiate` — Start Yoco checkout

**Newsletter & Reviews**
- `POST /api/newsletter/subscribe` — Subscribe to newsletter
- `POST /api/reviews` — Submit product review (moderation required)

### Admin API (requires Bearer token)

**Products** (`/api/admin/products`)
- `GET` — List all products with filters & sorting
- `POST` — Create product with variants
- `PUT /:id` — Update product fields
- `DELETE /:id` — Soft delete (archive) or permanent delete
- `POST /:id/mark-sold` — Mark product sold & auto-set archive date
- `POST /:id/images` — Upload image to Cloudinary
- `DELETE /:id/images/:imgId` — Delete product image

**Orders** (`/api/admin/orders`)
- `GET` — List orders with status/fulfillment filters
- `GET /:id` — Full order details
- `PUT /:id/status` — Update order status (with email notification)

**Categories** (`/api/admin/categories`)
- `POST` — Create category
- `PUT /:id` — Update category

**Instagram Sync** (`/api/admin/instagram`)
- `GET /posts` — Preview raw Instagram posts
- `POST /sync` — Pull new posts & create draft products

**Reviews** (`/api/admin/reviews`)
- `GET` — List reviews (filterable by approval status)
- `PUT /:id/approve` — Approve/reject review

## Setup

### Prerequisites

- Python 3.9+
- PostgreSQL 12+
- Redis (optional, for production rate limiting)

### Development

1. **Clone and navigate to project directory**
   ```bash
   cd midcenturist-api
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env with your local database & service credentials
   ```

5. **Initialize database**
   ```bash
   flask db upgrade
   ```

6. **Run development server**
   ```bash
   python run.py
   ```

Server runs at `http://localhost:5000/api`

### Database Migrations

```bash
# Create migration
flask db migrate -m "Description of change"

# Apply migration
flask db upgrade

# Revert migration
flask db downgrade
```

## API Documentation

### Health Check
```bash
GET /api/health
```

### Rate Limiting

Rate limits are applied per endpoint. Default policy:
- Public endpoints: 30-120 per minute depending on resource
- Admin endpoints: 3-5 per minute
- Newsletter: 3 per minute

Returns `429 Too Many Requests` when exceeded.

### Error Responses

All errors follow this format:
```json
{
  "error": "Human-readable error message",
  "details": "Optional additional info"
}
```

Status codes:
- `200` — Success
- `201` — Created
- `400` — Bad request (validation error)
- `401` — Unauthorized (missing/invalid token)
- `404` — Not found
- `409` — Conflict (e.g., duplicate slug)
- `410` — Gone (e.g., archived product)
- `422` — Unprocessable entity (validation error)
- `429` — Too many requests (rate limited)
- `500` — Server error

### Admin Authentication

Include Bearer token in request header:
```bash
Authorization: Bearer <token>
```

Token is a JWT signed with `ADMIN_JWT_SECRET`.

### Product Status

- `live` — Published, visible to public
- `draft` — Not yet published
- `sold` — Sold out, auto-archives after 30 days
- `archived` — Hidden from public, returns 410 Not Found

### Order Status

Flow: `pending` → `confirmed` → `paid` → `shipped` or `collected` → `delivered`

Alternative paths:
- `pending` → `cancelled` (before payment)
- Any → `cancelled` (manual cancellation)

### Payment Methods

**PayFast** (South Africa)
- Links to Hosted Payment Page for card entry
- Validates ITN webhook with MD5 signature
- Updates order status on completion

**Yoco** (South Africa)
- Tokenized payments (token acquired client-side)
- Instant completion
- Simpler webhook handling

## Deployment

### Production Configuration

1. **Set environment variables**
   ```bash
   export FLASK_ENV=production
   export DATABASE_URL=postgresql://user:pass@prod-host/db
   export SECRET_KEY=<strong-random-key>
   export ADMIN_JWT_SECRET=<strong-random-key>
   # Add PayFast, Yoco, Instagram, Resend, Cloudinary credentials
   ```

2. **Build & run with Gunicorn**
   ```bash
   pip install gunicorn
   gunicorn -w 4 -b 0.0.0.0:8000 wsgi:app
   ```

3. **Configure SSL/TLS** (e.g., via Nginx or managed platform)

4. **Set up monitoring** (e.g., Datadog, Sentry)

### Render.com Deployment

1. Create `render.yaml` (or use Render dashboard)
2. Link GitHub repo
3. Render auto-detects `requirements.txt` and `wsgi.py`
4. Add environment variables in dashboard
5. Deploy on push

### Database Backup

```bash
# Backup
pg_dump -U postgres -h localhost midcenturist_dev > backup.sql

# Restore
psql -U postgres -h localhost midcenturist_dev < backup.sql
```

## Architecture Notes

### Database

- **UUIDs** for all primary keys (PostgreSQL UUID type)
- **JSON columns** for flexible address storage (billing, shipping, collection)
- **Soft deletes** via `status` field for products (no hard deletes except admin override)
- **UTC timestamps** for all records
- **Indexes** on frequently-queried fields (slug, status, created_at)

### Caching

- Cart expires after 7 days of inactivity
- No server-side session storage (all state in requests)
- Product snapshots stored with orders (price-locking)

### Email

Placeholder implementation in `app/utils/email.py`. Integrate with:
- **Resend** — Modern email API (configured in settings)
- **SendGrid** — Alternative email provider
- **Postmark** — Email + inbound

### Image Storage

- **Cloudinary** for product images
- Auto-formatting & optimization
- Organized by product UUID (folder hierarchy)
- Images deleted from storage when product removed

### Security

- **Flask-Limiter** — Rate limiting
- **Flask-CORS** — Cross-origin requests (configurable origins)
- **Flask-Talisman** — Security headers (CSP disabled for API)
- **JWT** — Admin authentication (HS256)
- **HMAC** — PayFast signature verification

## Development Tips

### Test an endpoint locally

```bash
curl -X GET http://localhost:5000/api/products

curl -X POST http://localhost:5000/api/cart \
  -H "Content-Type: application/json"

curl -X GET http://localhost:5000/api/admin/products \
  -H "Authorization: Bearer <token>"
```

### Check database

```bash
# Connect to PostgreSQL
psql -U postgres -h localhost -d midcenturist_dev

# List tables
\dt

# Query products
SELECT id, name, status, created_at FROM products LIMIT 10;
```

### Generate admin token

```bash
from app.utils.security import generate_admin_token
token = generate_admin_token("admin@midcenturist.co.za")
# Use token in Authorization header
```

## Troubleshooting

### "ModuleNotFoundError: No module named 'app'"

Ensure you're running from project root and virtual environment is activated.

### Database connection error

Check `DATABASE_URL` in `.env`. Format:
```
postgresql://username:password@host:port/database_name
```

### CORS errors

Check `ALLOWED_ORIGINS` in `.env`. Frontend URL must be included.

### PayFast signature fails

Verify `PAYFAST_PASSPHRASE` is correct. Passphrase is case-sensitive and optional.

## License

Private — Midcenturist

## Support

Contact: [support contact info]
