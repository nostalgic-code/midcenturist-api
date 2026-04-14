# Midcenturist API — CMS Integration Guide

**Base URL:** `https://midcenturist-api.onrender.com`

All endpoints are prefixed with `/api`. Admin endpoints require a JWT token obtained from the login endpoint.

---

## Table of Contents

1. [Authentication](#1-authentication)
2. [Dashboard](#2-dashboard)
3. [Products (Admin)](#3-products-admin)
4. [Categories (Admin)](#4-categories-admin)
5. [Orders (Admin)](#5-orders-admin)
6. [Subscribers (Admin)](#6-subscribers-admin)
7. [Reviews (Admin)](#7-reviews-admin)
8. [Upcoming Items (Admin)](#8-upcoming-items-admin)
9. [Enquiries (Admin)](#9-enquiries-admin)
10. [Instagram Sync (Admin)](#10-instagram-sync-admin)
11. [Public Endpoints](#11-public-endpoints)
12. [Error Handling](#12-error-handling)

---

## 1. Authentication

All admin endpoints require the header:

```
Authorization: Bearer <token>
```

### POST `/api/admin/login`

Authenticate and receive a JWT token.

**Request:**
```json
{
  "email": "admin@example.com",
  "password": "your-password"
}
```

**Response (200):**
```json
{
  "token": "eyJhbGciOiJIUzI1NiIs...",
  "expires_in": 86400
}
```

**Errors:**
- `400` — Email and password are required
- `401` — Invalid email or password
- `429` — Rate limited (5 per minute)

---

## 2. Dashboard

### GET `/api/admin/dashboard`

Returns flat stats for the CMS dashboard.

**Response (200):**
```json
{
  "live_products": 12,
  "draft_products": 3,
  "sold_products": 5,
  "orders_this_month": 8,
  "pending_orders": 2,
  "total_subscribers": 45,
  "pending_reviews": 1,
  "drafts_from_instagram": 2
}
```

---

## 3. Products (Admin)

### GET `/api/admin/products`

List all products (all statuses).

**Query params:**
| Param      | Type   | Description                          |
|------------|--------|--------------------------------------|
| `status`   | string | Filter: `live`, `draft`, `sold`, `archived` |
| `category` | string | Filter by category slug              |
| `search`   | string | Search product name (ILIKE)          |
| `sort`     | string | `newest` (default), `price-high`, `price-low`, `name` |
| `page`     | int    | Page number (default: 1)             |
| `limit`    | int    | Items per page (default: 20, max: 50)|

**Response (200):**
```json
{
  "products": [
    {
      "id": "uuid",
      "name": "Teak Sideboard",
      "slug": "teak-sideboard",
      "description": "...",
      "era": "1960s",
      "material": "Solid Teak",
      "year": 1962,
      "condition": "Excellent",
      "status": "live",
      "badge": "New In",
      "is_featured": true,
      "is_unique": false,
      "category": { "id": "uuid", "name": "Sideboards", "slug": "sideboards", "parent_id": null },
      "instagram_post_id": null,
      "instagram_post_url": null,
      "sold_at": null,
      "archive_at": null,
      "created_at": "2025-01-15T10:30:00+00:00",
      "updated_at": "2025-01-15T10:30:00+00:00",
      "variants": [
        {
          "id": "uuid",
          "product_id": "uuid",
          "name": null,
          "price": 4500.00,
          "sale_price": null,
          "effective_price": 4500.00,
          "on_sale": false,
          "sku": "MCR-001",
          "stock_qty": 1,
          "is_available": true
        }
      ],
      "images": [
        {
          "id": "uuid",
          "product_id": "uuid",
          "variant_id": null,
          "url": "https://res.cloudinary.com/.../image.jpg",
          "alt_text": "Teak sideboard front view",
          "sort_order": 0,
          "is_primary": true
        }
      ],
      "primary_image": { "..." }
    }
  ],
  "total": 20,
  "page": 1,
  "limit": 20
}
```

### GET `/api/admin/products/:productId`

Get a single product by UUID (includes reviews).

**Response (200):** Single product object (same shape as above, plus `"reviews": [...]`).

### POST `/api/admin/products`

Create a new product.

**Request:**
```json
{
  "name": "Teak Sideboard",
  "description": "Beautiful mid-century piece...",
  "category_id": "uuid",
  "era": "1960s",
  "material": "Solid Teak",
  "year": 1962,
  "condition": "Excellent",
  "status": "draft",
  "badge": "New In",
  "is_featured": false,
  "is_unique": false,
  "price": 4500.00,
  "sale_price": null,
  "variants": [
    {
      "name": "Standard",
      "price": 4500.00,
      "sale_price": null,
      "sku": "MCR-001",
      "stock_qty": 1
    }
  ]
}
```

> If `variants` is omitted but `price` is provided, a default variant is created automatically.

**Response (201):** Full product object.

### PUT `/api/admin/products/:productId`

Update an existing product. Only send the fields you want to change.

**Request (partial):**
```json
{
  "name": "Updated Name",
  "status": "live",
  "badge": null
}
```

**Response (200):** Updated product object.

### POST `/api/admin/products/:productId/mark-sold`

Mark a product as sold. Sets `status=sold`, `sold_at`, `archive_at` (30 days later), and marks all variants unavailable.

**Response (200):** Updated product object.

### DELETE `/api/admin/products/:productId`

Soft-delete (archives) by default. Add `?permanent=true` for hard delete.

**Response (200):**
```json
{ "message": "Product archived" }
```

### POST `/api/admin/products/:productId/images`

Upload an image to Cloudinary.

**Request:** `multipart/form-data`
- `file` — Image file (required)
- `alt_text` — Alt text string (optional)

**Response (201):** Image object.

### DELETE `/api/admin/products/:productId/images/:imageId`

Delete a product image (also removes from Cloudinary).

**Response (200):**
```json
{ "message": "Image deleted" }
```

---

## 4. Categories (Admin)

### POST `/api/admin/categories`

Create a category.

**Request:**
```json
{
  "name": "Sideboards",
  "parent_id": null
}
```

**Response (201):** Category object.

### PUT `/api/admin/categories/:categoryId`

Update a category name or parent.

**Request:**
```json
{
  "name": "New Name",
  "parent_id": "uuid-or-null"
}
```

**Response (200):** Updated category object.

---

## 5. Orders (Admin)

### GET `/api/admin/orders`

List orders with filtering.

**Query params:**
| Param             | Type   | Description                                       |
|-------------------|--------|---------------------------------------------------|
| `status`          | string | `pending`, `confirmed`, `paid`, `shipped`, `collected`, `delivered`, `cancelled` |
| `fulfillment_type`| string | `collection` or `shipping`                        |
| `page`            | int    | Page number (default: 1)                          |
| `limit`           | int    | Items per page (default: 20, max: 50)             |

**Response (200):**
```json
{
  "orders": [
    {
      "id": "uuid",
      "order_number": "MCR-20250615-A1B2C3",
      "status": "pending",
      "fulfillment_type": "shipping",
      "total_amount": 4500.00,
      "notes": null,
      "created_at": "2025-06-15T...",
      "items": [...],
      "billing_address": { "name": "...", "email": "...", "phone": "..." },
      "shipping_address": { "..." },
      "collection_address": null,
      "payments": [...]
    }
  ],
  "total": 10,
  "page": 1
}
```

### GET `/api/admin/orders/:orderId`

Get a single order with full details.

**Response (200):** Single order object (same shape as above).

### PUT `/api/admin/orders/:orderId/status`

Update order status. Sends a status-update email to the customer.

**Request:**
```json
{
  "status": "confirmed"
}
```

**Valid statuses:** `pending`, `confirmed`, `paid`, `shipped`, `collected`, `delivered`, `cancelled`

**Response (200):** Updated order object.

---

## 6. Subscribers (Admin)

### GET `/api/admin/subscribers`

List newsletter subscribers with filtering.

**Query params:**
| Param    | Type   | Description                               |
|----------|--------|-------------------------------------------|
| `status` | string | `active` or `inactive`                    |
| `search` | string | Search by email, first name, or last name |
| `page`   | int    | Page number (default: 1)                  |
| `limit`  | int    | Items per page (default: 20, max: 50)     |

**Response (200):**
```json
{
  "subscribers": [
    {
      "id": "uuid",
      "email": "user@example.com",
      "first_name": "Jane",
      "last_name": "Doe",
      "phone": "+27...",
      "area": "Cape Town",
      "source": "footer",
      "is_active": true,
      "subscribed_at": "2025-01-10T..."
    }
  ],
  "total": 45,
  "page": 1,
  "limit": 20
}
```

### DELETE `/api/admin/subscribers/:subscriberId`

Permanently delete a subscriber.

**Response (200):**
```json
{ "message": "Subscriber deleted" }
```

---

## 7. Reviews (Admin)

### GET `/api/admin/reviews`

List reviews with optional approval filter.

**Query params:**
| Param     | Type   | Description                            |
|-----------|--------|----------------------------------------|
| `approved`| string | `true` or `false` to filter by status  |

**Response (200):**
```json
{
  "reviews": [
    {
      "id": "uuid",
      "product_id": "uuid",
      "reviewer_name": "John",
      "email": "john@example.com",
      "rating": 5,
      "comment": "Beautiful piece!",
      "is_approved": false,
      "created_at": "2025-01-12T...",
      "updated_at": "2025-01-12T..."
    }
  ]
}
```

### PUT `/api/admin/reviews/:reviewId/approve`

Approve or reject a review.

**Request:**
```json
{
  "approved": true
}
```

**Response (200):**
```json
{
  "message": "Review approved",
  "review": { "..." }
}
```

---

## 8. Upcoming Items (Admin)

### GET `/api/admin/upcoming`

List upcoming items.

**Query params:**
| Param    | Type   | Description                                                         |
|----------|--------|---------------------------------------------------------------------|
| `status` | string | `coming-soon`, `sourced`, `in-restoration`, `expected-this-week`    |
| `page`   | int    | Page number (default: 1)                                            |
| `limit`  | int    | Items per page (default: 20, max: 50)                               |

**Response (200):**
```json
{
  "upcoming": [
    {
      "id": "uuid",
      "name": "Danish Armchair",
      "description": "Original 1950s...",
      "estimated_price": 3200.00,
      "status": "in-restoration",
      "notify_count": 5,
      "sort_order": 0,
      "created_at": "2025-06-01T..."
    }
  ],
  "total": 3,
  "page": 1,
  "limit": 20
}
```

### POST `/api/admin/upcoming`

Create an upcoming item.

**Request:**
```json
{
  "name": "Danish Armchair",
  "description": "Original 1950s piece",
  "estimated_price": 3200.00,
  "status": "coming-soon",
  "sort_order": 0
}
```

**Response (201):** Upcoming item object.

### PUT `/api/admin/upcoming/:itemId`

Update an upcoming item. Send only the fields you want to change.

**Response (200):** Updated upcoming item object.

### DELETE `/api/admin/upcoming/:itemId`

Delete an upcoming item.

**Response (200):**
```json
{ "message": "Upcoming item deleted" }
```

### POST `/api/admin/upcoming/:itemId/convert`

Convert an upcoming item into a draft product. If `estimated_price` exists, a default variant is created. The upcoming item is deleted after conversion.

**Response (201):** The new product object.

---

## 9. Enquiries (Admin)

### GET `/api/admin/enquiries`

List contact form enquiries.

**Query params:**
| Param    | Type   | Description                          |
|----------|--------|--------------------------------------|
| `status` | string | `unread`, `read`, `replied`          |
| `page`   | int    | Page number (default: 1)             |
| `limit`  | int    | Items per page (default: 20, max: 50)|

**Response (200):**
```json
{
  "enquiries": [
    {
      "id": "uuid",
      "name": "Jane Doe",
      "email": "jane@example.com",
      "phone": "+27...",
      "message": "I'm interested in...",
      "status": "unread",
      "created_at": "2025-06-12T...",
      "updated_at": "2025-06-12T..."
    }
  ],
  "total": 5,
  "page": 1,
  "limit": 20
}
```

### PATCH `/api/admin/enquiries/:enquiryId`

Update enquiry status (e.g., mark as read/replied).

**Request:**
```json
{
  "status": "read"
}
```

**Response (200):** Updated enquiry object.

---

## 10. Instagram Sync (Admin)

### POST `/api/admin/instagram/sync`

Pull latest posts from Instagram and create draft products for new ones.

**Response (200):**
```json
{
  "synced": 3,
  "new_drafts": [
    { "post_id": "17...", "name": "Mid-century chair" }
  ],
  "message": "3 new draft(s) created"
}
```

**Rate limit:** 5 per hour

### GET `/api/admin/instagram/posts`

Preview raw Instagram posts (shows which are already imported).

**Response (200):**
```json
{
  "posts": [
    {
      "id": "17...",
      "caption": "Beautiful teak...",
      "media_url": "https://...",
      "permalink": "https://www.instagram.com/p/...",
      "timestamp": "2025-06-01T...",
      "already_imported": false
    }
  ]
}
```

---

## 11. Public Endpoints

These do NOT require authentication.

### Products

| Method | Endpoint                      | Description                        |
|--------|-------------------------------|------------------------------------|
| GET    | `/api/products`               | List live products (paginated)     |
| GET    | `/api/products/search?q=...`  | Search products by name/material   |
| GET    | `/api/products/:slug`         | Get product by slug (with reviews) |

**`/api/products` query params:** `category`, `collection`, `status`, `featured`, `badge`, `page`, `limit`

### Categories & Collections

| Method | Endpoint                               | Description                      |
|--------|----------------------------------------|----------------------------------|
| GET    | `/api/categories`                      | Category tree with product counts|
| GET    | `/api/categories/:slug/products`       | Products in a category           |
| GET    | `/api/collections`                     | All active collections           |
| GET    | `/api/collections/:slug/products`      | Products in a collection         |

### Cart

| Method | Endpoint                                   | Description           |
|--------|--------------------------------------------|-----------------------|
| POST   | `/api/cart`                                | Create new cart       |
| GET    | `/api/cart/:sessionId`                     | Get cart              |
| POST   | `/api/cart/:sessionId/items`               | Add item to cart      |
| PUT    | `/api/cart/:sessionId/items/:itemId`       | Update item qty       |
| DELETE | `/api/cart/:sessionId`                     | Clear cart            |

### Orders

| Method | Endpoint       | Description   |
|--------|----------------|---------------|
| POST   | `/api/orders`  | Place an order|

### Newsletter

| Method | Endpoint                     | Description              |
|--------|------------------------------|--------------------------|
| POST   | `/api/newsletter/subscribe`  | Subscribe to newsletter  |

### Reviews

| Method | Endpoint        | Description                         |
|--------|-----------------|-------------------------------------|
| POST   | `/api/reviews`  | Submit a review (pending approval)  |

### Health Check

| Method | Endpoint      | Description       |
|--------|---------------|-------------------|
| GET    | `/api/health` | Returns `{ "status": "ok" }` |

---

## 12. Error Handling

All errors return JSON with an `error` key:

```json
{ "error": "Product not found" }
```

Validation errors return an `errors` array:

```json
{ "errors": ["name is required", "price must be a positive number"] }
```

**Common HTTP status codes:**
| Code | Meaning                    |
|------|----------------------------|
| 200  | Success                    |
| 201  | Created                    |
| 400  | Bad request                |
| 401  | Unauthorized (missing/invalid token) |
| 404  | Not found                  |
| 409  | Conflict (duplicate, stock issue) |
| 410  | Gone (expired cart)        |
| 422  | Validation errors          |
| 429  | Rate limited               |
| 500  | Server error               |
| 502  | Upstream error (Instagram) |
| 503  | Service not configured     |
