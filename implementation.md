# Midcenturist API Implementation Guide

A comprehensive overview of the Flask-based REST API for Midcenturist, a mid-century modern furniture e-commerce platform. This document covers database models, API endpoints, schemas, utility functions, and architectural patterns.

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Database Models & Schemas](#database-models--schemas)
3. [API Routes & Endpoints](#api-routes--endpoints)
4. [Utility Functions](#utility-functions)
5. [Configuration & Extensions](#configuration--extensions)
6. [Security & Authentication](#security--authentication)

---

## Architecture Overview

**Framework:** Flask 3.0.3  
**Database:** PostgreSQL 12+ (SQLAlchemy ORM)  
**Deployment:** Gunicorn on Render  
**Authentication:** JWT-based admin tokens  
**Payment Gateways:** PayFast, Yoco  
**Email Service:** Resend  
**Image Storage:** Cloudinary  

### Project Structure

```
app/
├── __init__.py              # App factory, blueprint registration
├── extensions.py            # Extensions (db, migrate, cors, limiter, talisman)
├── models/
│   └── __init__.py         # All database models
├── routes/
│   ├── __init__.py
│   ├── products.py         # Product listing, search, detail
│   ├── categories.py       # Category tree, collections
│   ├── cart.py             # Shopping cart operations
│   ├── orders.py           # Order creation, tracking
│   ├── payments.py         # Payment webhooks
│   ├── newsletter.py       # Email subscription
│   └── admin/
│       ├── __init__.py
│       ├── products.py     # CRUD for products/variants/images
│       ├── orders.py       # Order management
│       └── ...
└── utils/
    ├── __init__.py
    ├── email.py            # Email sending (Resend)
    ├── security.py         # JWT, PayFast signatures
    └── validators.py       # Input validation

config.py                    # Configuration by environment
wsgi.py                      # WSGI entry point for Gunicorn
run.py                       # Development server runner
```

---

## Database Models & Schemas

### Core Tables

All tables use **UUID primary keys** and **timezone-aware timestamps**. Foreign keys use PostgreSQL UUID type with proper cascade behaviors.

#### 1. **Categories** (`categories` table)

Hierarchical category structure for product organization.

| Column | Type | Null | Unique | Notes |
|--------|------|------|--------|-------|
| id | UUID | N | Y | PK, auto-generated |
| name | VARCHAR(255) | N | N | Display name |
| slug | VARCHAR(255) | N | Y | URL-friendly identifier |
| parent_id | UUID | Y | N | FK to self for hierarchy |
| created_at | DateTime(TZ) | N | N | ISO 8601 UTC |

**Relationships:**
- `1:N` with Products (on `product.category_id`)
- `1:N` self-referential (parent → children)

**Methods:**
- `to_dict(include_children=False)` — Serialize with optional tree

**Sample Query:**
```python
# Get category and all products
cat = Category.query.filter_by(slug="chairs").first()
products = Product.query.filter(
    Product.category_id.in_([cat.id] + [c.id for c in cat.children]),
    Product.status == "live"
).all()
```

---

#### 2. **Collections** (`collections` table)

Groupings of products (e.g., "Summer Sale", "Designer Picks"). Uses N:N relationship with Products.

| Column | Type | Null | Unique | Notes |
|--------|------|------|--------|-------|
| id | UUID | N | Y | PK |
| name | VARCHAR(255) | N | N | Display name |
| slug | VARCHAR(255) | N | Y | URL identifier |
| description | TEXT | Y | N | Promo text |
| is_active | BOOLEAN | N | N | Default: true |
| created_at | DateTime(TZ) | N | N | |

**Join Table:** `product_collections` (product_id, collection_id)

---

#### 3. **Products** (`products` table)

Main product entity with rich metadata for mid-century furniture.

| Column | Type | Null | Unique | Notes |
|--------|------|------|--------|-------|
| id | UUID | N | Y | PK |
| name | VARCHAR(255) | N | N | Product title |
| slug | VARCHAR(255) | N | Y | URL-friendly |
| description | TEXT | Y | N | Rich description |
| price | Numeric(10,2) | N | N | **[DEPRECATED]** Use ProductVariant.price |
| category_id | UUID | Y | N | FK to Categories |
| **era** | VARCHAR(100) | Y | N | e.g., "1962", "1960s" |
| **material** | VARCHAR(255) | Y | N | e.g., "Solid Teak", "Walnut" |
| **year** | INTEGER | Y | N | Manufacture year |
| **condition** | VARCHAR(50) | Y | N | Excellent \| Very Good \| Good \| Restored |
| status | VARCHAR(20) | N | N | live \| draft \| sold \| archived |
| badge | VARCHAR(20) | Y | N | New In \| Last One \| Sale |
| is_featured | BOOLEAN | N | N | Featured on homepage |
| is_unique | BOOLEAN | N | N | Appears in 2 homepage spots |
| instagram_post_id | VARCHAR(255) | Y | N | Meta Graph API post ID |
| instagram_post_url | VARCHAR(500) | Y | N | Link to Instagram post |
| sold_at | DateTime(TZ) | Y | N | Marks as sold |
| archive_at | DateTime(TZ) | Y | N | Auto 30 days after sold_at |
| created_at | DateTime(TZ) | N | N | |
| updated_at | DateTime(TZ) | N | N | Auto-updated on change |

**Relationships:**
- `N:1` Category (on `category_id`)
- `1:N` ProductVariant (cascade delete)
- `1:N` ProductImage (cascade delete, ordered by `sort_order`)
- `1:N` Review (cascade delete)
- `N:N` Collection (via `product_collections` join table)

**Properties:**
- `primary_image` — Returns first `ProductImage` where `is_primary=true`, else first image
- `effective_price` — Convenience property (use Variant instead)

**Methods:**
- `to_dict(include_variants=True, include_images=True, include_reviews=False)` — Full serialization

---

#### 4. **ProductVariants** (`product_variants` table)

Prices and stock at the variant level (size, color, material combo).

| Column | Type | Null | Unique | Notes |
|--------|------|------|--------|-------|
| id | UUID | N | Y | PK |
| product_id | UUID | N | N | FK to Products |
| name | VARCHAR(255) | Y | N | e.g., "Walnut / Large", "Teak / Small" |
| price | Numeric(10,2) | N | N | Regular price |
| sale_price | Numeric(10,2) | Y | N | Discounted price if on sale |
| sku | VARCHAR(100) | Y | Y | Stock keeping unit |
| stock_qty | INTEGER | N | N | Inventory count (default 1) |
| is_available | BOOLEAN | N | N | Enabled for purchase |

**Properties:**
- `effective_price` — Returns `sale_price` if set, else `price`
- `on_sale` — True if `sale_price < price`

**Methods:**
- `to_dict()` — Includes computed properties

---

#### 5. **ProductImages** (`product_images` table)

Image storage with sort order and variant specificity.

| Column | Type | Null | Unique | Notes |
|--------|------|------|--------|-------|
| id | UUID | N | Y | PK |
| product_id | UUID | N | N | FK to Products |
| variant_id | UUID | Y | N | FK to ProductVariants (optional) |
| url | VARCHAR(500) | N | N | Cloudinary URL |
| alt_text | VARCHAR(255) | Y | N | Accessibility text |
| sort_order | INTEGER | N | N | Display order (default 0) |
| is_primary | BOOLEAN | N | N | Featured thumbnail |

---

#### 6. **Cart** & **CartItem** (`carts`, `cart_items` tables)

Client-side shopping cart model (session-based, no user accounts).

**Carts:**

| Column | Type | Null | Unique | Notes |
|--------|------|------|--------|-------|
| id | UUID | N | Y | PK |
| session_id | VARCHAR(255) | N | Y | Client session identifier |
| expires_at | DateTime(TZ) | N | N | Expiry for cleanup |
| created_at | DateTime(TZ) | N | N | |
| updated_at | DateTime(TZ) | N | N | |

**Properties:**
- `is_expired` — True if `expires_at < now()`

**CartItems:**

| Column | Type | Null | Unique | Notes |
|--------|------|------|--------|-------|
| id | UUID | N | Y | PK |
| cart_id | UUID | N | N | FK to Cart (CASCADE on delete) |
| product_variant_id | UUID | N | N | FK to ProductVariant |
| quantity | INTEGER | N | N | Default 1 |
| added_at | DateTime(TZ) | N | N | |

---

#### 7. **Orders** (`orders` table)

All orders with fulfillment and payment tracking.

| Column | Type | Null | Unique | Notes |
|--------|------|------|--------|-------|
| id | UUID | N | Y | PK |
| order_number | VARCHAR(32) | N | Y | Unique reference (e.g., MCR-20260414-ABC123) |
| status | VARCHAR(20) | N | N | pending \| confirmed \| paid \| shipped \| collected \| delivered \| cancelled |
| fulfillment_type | VARCHAR(20) | N | N | collection \| shipping |
| total_amount | Numeric(10,2) | N | N | Order total in ZAR |
| billing_address | JSONB | N | N | {name, email, phone, address_line1, city, province, postal_code} |
| shipping_address | JSONB | Y | N | Only if fulfillment_type=shipping |
| collection_address | JSONB | Y | N | Only if fulfillment_type=collection |
| notes | TEXT | Y | N | Special instructions |
| created_at | DateTime(TZ) | N | N | |

**Relationships:**
- `1:N` OrderItem (cascade delete)
- `1:N` Payment (cascade delete)

**Methods:**
- `to_dict(admin=False)` — Sensitive fields hidden unless `admin=true`

---

#### 8. **OrderItems** (`order_items` table)

Line items with price snapshots.

| Column | Type | Null | Unique | Notes |
|--------|------|------|--------|-------|
| id | UUID | N | Y | PK |
| order_id | UUID | N | N | FK to Orders |
| product_variant_id | UUID | N | N | FK to ProductVariant |
| quantity | INTEGER | N | N | Qty ordered |
| price_at_purchase | Numeric(10,2) | N | N | **Locked at order time** |
| product_snapshot | JSONB | Y | N | {product_name, variant_name, ...} for history |

---

#### 9. **Payments** (`payments` table)

Payment transaction history.

| Column | Type | Null | Unique | Notes |
|--------|------|------|--------|-------|
| id | UUID | N | Y | PK |
| order_id | UUID | N | N | FK to Orders |
| method | VARCHAR(20) | N | N | payfast \| yoco |
| status | VARCHAR(20) | N | N | initiated \| completed \| failed \| cancelled |
| amount | Numeric(10,2) | N | N | Payment amount |
| transaction_id | VARCHAR(255) | Y | N | Gateway transaction ID |
| paid_at | DateTime(TZ) | Y | N | Completion timestamp |
| raw_webhook | JSONB | Y | N | Full webhook payload for debugging |

---

#### 10. **Reviews** (Planned)

Customer product reviews (moderated).

```python
class Review(db.Model):
    __tablename__ = "reviews"
    
    id = uuid_pk()
    product_id = UUID FK
    rating = INTEGER (1-5)
    title = VARCHAR(255)
    comment = TEXT
    author_name = VARCHAR(100)
    is_approved = BOOLEAN (default: False, requires moderation)
    created_at = DateTime(TZ)
```

---

### Database Migrations

Using **Flask-Migrate** with Alembic:

```bash
# Generate migration after model changes
flask db migrate -m "Add product condition field"

# Apply migrations
flask db upgrade

# Downgrade
flask db downgrade
```

---

## API Routes & Endpoints

### Public Routes (Rate Limited)

#### Products

**`GET /api/products`** — List all products (paginated, filterable)

Query Parameters:
- `category` (slug) — Filter by category
- `collection` (slug) — Filter by collection
- `status` (default: "live") — live|draft|sold|archived
- `featured` (true/false) — Only featured products
- `badge` (string) — Filter by badge (New In|Last One|Sale)
- `page` (int, default: 1) — Pagination
- `limit` (int, default: 24, max: 48) — Items per page

Response:
```json
{
  "products": [
    {
      "id": "uuid",
      "name": "Teak Sideboard",
      "slug": "teak-sideboard",
      "status": "live",
      "material": "Solid Teak",
      "year": 1962,
      "era": "1960s",
      "condition": "Excellent",
      "badge": "Last One",
      "is_featured": true,
      "price": 4500,
      "variants": [...],
      "images": [...],
      "created_at": "2026-04-14T10:00:00+00:00"
    }
  ],
  "total": 127,
  "page": 1,
  "pages": 6
}
```

Rate Limit: 60/min

---

**`GET /api/products/search`** — Full-text search

Query Parameters:
- `q` (string, min: 2 chars) — Search query

Response:
```json
{
  "products": [...],
  "total": 5,
  "query": "teak sideboard"
}
```

Rate Limit: 30/min

---

**`GET /api/products/<slug>`** — Product detail

Response:
```json
{
  "id": "uuid",
  "name": "Teak Sideboard",
  ...full product details...,
  "variants": [
    {
      "id": "variant-uuid",
      "name": "Natural / Large",
      "price": 4500,
      "sale_price": null,
      "sku": "TEAK-SB-001",
      "stock_qty": 1,
      "effective_price": 4500,
      "on_sale": false
    }
  ],
  "images": [
    {
      "id": "img-uuid",
      "url": "https://res.cloudinary.com/...",
      "is_primary": true
    }
  ],
  "reviews": [
    {
      "rating": 5,
      "author": "Jane D.",
      "comment": "Perfect condition!"
    }
  ]
}
```

Rate Limit: 120/min

---

#### Categories

**`GET /api/categories`** — Full category tree with product counts

Response:
```json
{
  "categories": [
    {
      "id": "uuid",
      "name": "Chairs",
      "slug": "chairs",
      "product_count": 23,
      "children": [
        {
          "id": "uuid",
          "name": "Dining Chairs",
          "slug": "dining-chairs",
          "product_count": 8,
          "children": []
        }
      ]
    }
  ]
}
```

---

**`GET /api/categories/<slug>/products`** — Products in category (includes subcategories)

Response:
```json
{
  "category": {...},
  "products": [...],
  "total": 23
}
```

---

**`GET /api/collections`** — Active collections

Response:
```json
{
  "collections": [
    {
      "id": "uuid",
      "name": "Summer Sale 2026",
      "slug": "summer-sale-2026",
      "description": "20% off selected pieces",
      "is_active": true,
      "product_count": 12
    }
  ]
}
```

---

#### Cart

**`POST /api/cart`** — Initialize or get cart

Body:
```json
{
  "session_id": "unique-session-hash"
}
```

Response:
```json
{
  "id": "uuid",
  "session_id": "...",
  "expires_at": "2026-04-21T10:00:00+00:00",
  "items": [],
  "total": 0
}
```

---

**`POST /api/cart/items`** — Add item to cart

Body:
```json
{
  "session_id": "...",
  "product_variant_id": "uuid",
  "quantity": 1
}
```

Response: Updated cart object

---

**`DELETE /api/cart/items/<item_id>`** — Remove item from cart

Response: Updated cart object

---

**`PATCH /api/cart/items/<item_id>`** — Update quantity

Body:
```json
{
  "quantity": 2
}
```

---

#### Orders

**`POST /api/orders`** — Create order from cart

Body:
```json
{
  "session_id": "...",
  "fulfillment_type": "shipping|collection",
  "billing_address": {
    "name": "John Doe",
    "email": "john@example.com",
    "phone": "+27123456789",
    "address_line1": "123 Main St",
    "city": "Cape Town",
    "province": "Western Cape",
    "postal_code": "8000"
  },
  "shipping_address": { /* if fulfillment_type: shipping */ },
  "collection_address": { /* if fulfillment_type: collection */ },
  "notes": "Please leave at front door"
}
```

Default Status: `pending`

Response:
```json
{
  "id": "uuid",
  "order_number": "MCR-20260414-ABC123",
  "status": "pending",
  "total_amount": 4500,
  "items": [
    {
      "quantity": 1,
      "price_at_purchase": 4500,
      "line_total": 4500,
      "product_snapshot": {...}
    }
  ]
}
```

Rate Limit: 3/min

---

**`GET /api/orders/<order_id>`** — Get order detail (public, limited fields)

Response excludes `billing_address`, `shipping_address` unless customer authenticated

---

#### Payments

**`POST /api/payments/payfast/notify`** — PayFast ITN webhook

Used by PayFast to notify of payment status. Validates HMAC signature.

Body (form-encoded):
```
m_payment_id=order-id
payment_status=COMPLETE
pf_payment_id=transaction-id
signature=md5-hash
```

Updates Order.status to `approved|failed` and records Payment.

---

**`GET /api/payments/yoco/callback`** — Yoco payment callback

Query: `checkoutId`, `status`

Initiates Yoco verification request.

---

#### Newsletters

**`POST /api/newsletter/subscribe`** — Join mailing list

Body:
```json
{
  "email": "user@example.com",
  "name": "John Doe"
}
```

Response:
```json
{
  "message": "Subscription successful"
}
```

---

### Admin Routes (JWT Protected)

All admin routes require:
```
Authorization: Bearer <jwt_token>
```

Admin token generated via login (not yet exposed; typically via secure admin panel).

#### Product Management

**`POST /api/admin/products`** — Create product

Body:
```json
{
  "name": "Teak Sideboard",
  "slug": "teak-sideboard",
  "description": "1960s Danish design...",
  "category_id": "uuid",
  "era": "1960s",
  "material": "Solid Teak",
  "year": 1962,
  "condition": "Excellent",
  "status": "draft",
  "badge": null,
  "is_featured": false,
  "is_unique": false,
  "instagram_post_id": null,
  "instagram_post_url": null
}
```

Response: Created product object

---

**`PATCH /api/admin/products/<product_id>`** — Update product

Same schema as POST

---

**`DELETE /api/admin/products/<product_id>`** — Delete product (cascades variants, images, reviews)

---

**`POST /api/admin/products/<product_id>/variants`** — Add product variant

Body:
```json
{
  "name": "Natural / Large",
  "price": 4500.00,
  "sale_price": null,
  "sku": "TEAK-SB-001",
  "stock_qty": 1
}
```

---

**`PATCH /api/admin/products/<product_id>/variants/<variant_id>`** — Update variant

---

**`POST /api/admin/products/<product_id>/images`** — Upload product image

Multipart form:
```
file: <image file>
alt_text: "Teak sideboard front view"
sort_order: 0
is_primary: true
variant_id: "uuid" (optional)
```

Uses Cloudinary for storage.

---

#### Order Management

**`GET /api/admin/orders`** — List all orders (paginated)

Query:
- `status` — Filter by status
- `fulfillment_type` — collection|shipping
- `sort` — created_at|status
- `page`, `limit`

Response includes full billing/shipping addresses (admin view)

---

**`PATCH /api/admin/orders/<order_id>`** — Update order status

Body:
```json
{
  "status": "confirmed|paid|shipped|collected|delivered|cancelled"
}
```

Triggers email notification to customer.

---

**`GET /api/admin/orders/<order_id>/payments`** — View payment history

Response:
```json
{
  "payments": [
    {
      "id": "uuid",
      "method": "payfast",
      "status": "completed",
      "amount": 4500,
      "transaction_id": "123456",
      "paid_at": "2026-04-14T10:30:00+00:00"
    }
  ]
}
```

---

### Health Check

**`GET /api/health`** — API status

Response:
```json
{
  "status": "ok",
  "env": "production|development"
}
```

---

## Utility Functions

### Security (`app/utils/security.py`)

#### JWT Admin Authentication

**`require_admin` (decorator)**
```python
from app.utils.security import require_admin

@app.route("/admin/products", methods=["POST"])
@require_admin
def create_product():
    # Only called if valid Bearer token provided
    ...
```

Validates Bearer token using `ADMIN_JWT_SECRET`. Returns `401` if missing/invalid/expired.

---

**`generate_admin_token(email: str, expires_hours: int = 24) -> str`**

Issues JWT with:
- `sub` (subject): email address
- `iat` (issued at): current UTC timestamp
- `exp` (expiry): current time + hours

Used by admin login endpoint.

Example:
```python
token = generate_admin_token("admin@midcenturist.co.za", expires_hours=24)
# Returns: eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...
```

---

#### PayFast Signatures

**`generate_payfast_signature(data: dict, passphrase: str = None) -> str`**

MD5 signature for PayFast requests:
1. Sort data keys alphabetically
2. Build query string: `key1=val1&key2=val2&...`
3. Append passphrase (if provided)
4. Compute MD5 hash

Example:
```python
sig = generate_payfast_signature({
    "merchant_id": "10000100",
    "merchant_key": "xxxx",
    "return_url": "...",
    "notify_url": "...",
}, passphrase="MyPassPhrase")
```

---

**`verify_payfast_itn(post_data: dict, passphrase: str = None) -> bool`**

Validates incoming PayFast Instant Transaction Notification (ITN):
1. Extracts `signature` from POST data
2. Recomputes expected signature
3. Constant-time comparison to prevent timing attacks

Returns `True` if signatures match.

---

### Validators (`app/utils/validators.py`)

**`validate_checkout(data: dict) -> list`**

Validates checkout form data. Returns list of error messages (empty if valid).

Checks:
- Required fields present: `session_id`, `fulfillment_type`, `billing_address`
- Email format valid
- Phone format valid (basic regex)
- Required address fields based on fulfillment type
- Fulfillment type is `collection` or `shipping`

Example:
```python
errors = validate_checkout(request.get_json())
if errors:
    return jsonify({"errors": errors}), 422
```

---

### Email (`app/utils/email.py`)

**`send_order_confirmation(order: Order)`**

Sends customer-facing confirmation email via Resend API with:
- Order number
- Item list
- Total amount
- Fulfillment address

---

**`send_order_notification(order: Order)`**

Sends internal notification to `CLIENT_EMAIL` of new order.

---

**`send_status_update(order: Order)`**

Notifies customer of order status change (shipped/collected/delivered).

---

## Configuration & Extensions

### Config (`config.py`)

**Base Config:**
```python
class Config:
    SECRET_KEY: str              # Flask session signing
    SQLALCHEMY_TRACK_MODIFICATIONS: bool = False
    WTF_CSRF_ENABLED: bool = True
    ADMIN_JWT_SECRET: str        # JWT signing key
    
    # Payment gateways
    PAYFAST_MERCHANT_ID: str
    PAYFAST_MERCHANT_KEY: str
    PAYFAST_PASSPHRASE: str
    PAYFAST_SANDBOX: bool       # Dev mode
    
    YOCO_SECRET_KEY: str
    YOCO_SANDBOX: bool          # Dev mode
    
    # Instagram integration
    INSTAGRAM_ACCESS_TOKEN: str
    INSTAGRAM_BUSINESS_ACCOUNT_ID: str
    
    # Email (Resend)
    RESEND_API_KEY: str
    CLIENT_EMAIL: str
    FROM_EMAIL: str = "noreply@midcenturist.co.za"
    
    # Image storage
    CLOUDINARY_URL: str
    
    # CORS
    ALLOWED_ORIGINS: list[str]
    
    # Rate limiting
    RATELIMIT_STORAGE_URL: str  # Redis or "memory://"
```

**Development Config:**
```python
class DevelopmentConfig(Config):
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = "postgresql://postgres:postgres@localhost/midcenturist_dev"
    WTF_CSRF_ENABLED = False
```

**Production Config:**
```python
class ProductionConfig(Config):
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = "postgresql://..." # from DATABASE_URL env var
```

---

### Extensions (`app/extensions.py`)

**`db` (SQLAlchemy)**
ORM for database operations. Initialized in `create_app()`.

```python
db.session.add(product)
db.session.commit()
```

---

**`migrate` (Flask-Migrate)**
Alembic integration for schema migrations.

```bash
flask db migrate -m "description"
flask db upgrade
```

---

**`cors` (Flask-CORS)**
Cross-origin requests allowed from `ALLOWED_ORIGINS`.

```python
cors.init_app(
    app,
    resources={r"/api/*": {"origins": app.config["ALLOWED_ORIGINS"]}},
    supports_credentials=True
)
```

---

**`limiter` (Flask-Limiter)**
Rate limiting by IP address. Storage: Redis (prod) or in-memory (dev).

Applied per-endpoint:
```python
@app.route("/api/products")
@limiter.limit("60 per minute")
def list_products():
    ...
```

---

**`talisman` (Flask-Talisman)**
Security headers:
- `Strict-Transport-Security` (HTTPS in prod)
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY` (prevents clickjacking)
- CSP disabled (API, no HTML responses)

---

## Security & Authentication

### CORS Policy

Only requests from whitelisted origins allowed:
```
https://midcenturist.co.za
https://www.midcenturist.co.za
http://localhost:3000
http://localhost:3001
```

Credentials (cookies, auth headers) supported.

---

### JWT Admin Authentication

1. **Token Generation:**
   ```python
   token = generate_admin_token("admin@site.com")
   ```

2. **Token Usage (Client):**
   ```
   Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...
   ```

3. **Validation (Server):**
   ```python
   @require_admin
   def create_product():
       # Decorator validates token
       ...
   ```

**Default Expiration:** 24 hours

---

### Payment Gateway Security

**PayFast:**
- MD5 signature validation on ITN callbacks
- Merchant ID, Key, Passphrase stored in env vars
- Webhook IP whitelist (via Render env config)

**Yoco:**
- API key stored in env var
- Checkouts verified server-side

---

### Rate Limiting Strategy

| Endpoint | Limit | Purpose |
|----------|-------|---------|
| `/api/products` | 60/min | List operations (cacheable) |
| `/api/products/search` | 30/min | Full-text search (CPU intensive) |
| `/api/products/<slug>` | 120/min | Detail view (cacheable) |
| `/api/orders` | 3/min | Order creation (critical operation) |
| Admin endpoints | 10/min | General protection |

Limit by IP via Flask-Limiter.

---

### Database Constraints

- **UUID PKs:** Prevent ID enumeration
- **Unique Slugs:** Prevent duplicates
- **SKU Uniqueness:** Variant identification
- **Cascade Deletes:** Maintain referential integrity
- **NOT NULL Constraints:** Enforce data validity
- **Numeric Precision:** Accurate pricing (Numeric(10,2))

---

## Development Workflow

### Local Setup

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create .env file
cat > .env << EOF
FLASK_ENV=development
SECRET_KEY=dev-key-change-in-production
ADMIN_JWT_SECRET=admin-secret
DATABASE_URL=postgresql://user:pass@localhost/midcenturist_dev
EOF

# Initialize database
flask db upgrade

# Run development server
python run.py
# API at http://localhost:5000
```

---

### Testing an Endpoint

**Products Listing:**
```bash
curl "http://localhost:5000/api/products?page=1&limit=10"
```

**Create Product (Admin):**
```bash
TOKEN=$(curl -X POST http://localhost:5000/api/admin/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@site.com","password":"xxx"}' \
  | jq -r '.token')

curl -X POST http://localhost:5000/api/admin/products \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name":"Teak Chair",
    "slug":"teak-chair",
    "description":"1960s Danish",
    "material":"Teak",
    "year":1962,
    "status":"draft"
  }'
```

---

### Production Deployment

**Environment Variables (Render):**
```
FLASK_ENV=production
SECRET_KEY=<generate-secure>
ADMIN_JWT_SECRET=<generate-secure>
DATABASE_URL=postgresql://...
PAYFAST_MERCHANT_ID=<merchant-id>
PAYFAST_MERCHANT_KEY=<merchant-key>
PAYFAST_PASSPHRASE=<passphrase>
YOCO_SECRET_KEY=<key>
RESEND_API_KEY=<api-key>
CLOUDINARY_URL=cloudinary://<key>:<secret>@<cloud>
INSTAGRAM_ACCESS_TOKEN=<token>
INSTAGRAM_BUSINESS_ACCOUNT_ID=<id>
```

**Start Command (Render):**
```
gunicorn -w 1 -b 0.0.0.0:8000 --timeout 600 wsgi:app
```

**Build Command (Render):**
```
pip install -r requirements.txt
```

---

## Future Enhancements

1. **Reviews System:** Moderate and display customer reviews per product
2. **Redis Caching:** Cache product listings and category trees
3. **Full-Text Search:** PostgreSQL tsvector index for faster searches
4. **Admin Panel:** React frontend for product/order management
5. **Inventory Alerts:** Notify when stock < threshold
6. **Email Notifications:** Full Resend integration templates
7. **Stripe/Square:** Additional payment gateway options
8. **Wishlist:** Customer favorites (requires user accounts)
9. **Analytics:** Track views, conversions, popular items
10. **Image Optimization:** Automatic image resizing via Cloudinary

---

## References

- [Flask Documentation](https://flask.palletsprojects.com/)
- [SQLAlchemy ORM](https://docs.sqlalchemy.org/en/20/)
- [Flask-SQLAlchemy](https://flask-sqlalchemy.palletsprojects.io/)
- [PayFast API](https://www.payfast.co.za/documentation/)
- [Yoco Payments](https://yocotech.atlassian.net/wiki/spaces/YDS/overview)
- [Cloudinary SDK](https://cloudinary.com/documentation/python_integration)
- [Resend Email API](https://resend.com/docs)

---

**Revision:** 1.0  
**Last Updated:** 2026-04-14  
**Author:** Midcenturist Development Team
