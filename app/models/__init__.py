import uuid
from datetime import datetime, timezone
from app.extensions import db
from sqlalchemy.dialects.postgresql import UUID, JSONB
import sqlalchemy as sa

# ─── helpers ────────────────────────────────────────────────────────────────

def uuid_pk():
    return db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

def now_utc():
    return datetime.now(timezone.utc)


# ─── categories ─────────────────────────────────────────────────────────────

class Category(db.Model):
    __tablename__ = "categories"

    id = uuid_pk()
    name = db.Column(db.String(255), nullable=False)
    slug = db.Column(db.String(255), unique=True, nullable=False)
    parent_id = db.Column(UUID(as_uuid=True), db.ForeignKey("categories.id"), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), default=now_utc)

    products = db.relationship("Product", back_populates="category")
    children = db.relationship("Category", backref=db.backref("parent", remote_side=[id]))

    def to_dict(self, include_children=False):
        d = {
            "id": str(self.id),
            "name": self.name,
            "slug": self.slug,
            "parent_id": str(self.parent_id) if self.parent_id else None,
        }
        if include_children:
            d["children"] = [c.to_dict() for c in self.children]
        return d


# ─── collection ─────────────────────────────────────────────────────────────

product_collections = db.Table(
    "product_collections",
    db.Column("product_id", UUID(as_uuid=True), db.ForeignKey("products.id"), primary_key=True),
    db.Column("collection_id", UUID(as_uuid=True), db.ForeignKey("collections.id"), primary_key=True),
)


class Collection(db.Model):
    __tablename__ = "collections"

    id = uuid_pk()
    name = db.Column(db.String(255), nullable=False)
    slug = db.Column(db.String(255), unique=True, nullable=False)
    description = db.Column(db.Text, nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime(timezone=True), default=now_utc)

    products = db.relationship("Product", secondary=product_collections, back_populates="collections")

    def to_dict(self):
        return {
            "id": str(self.id),
            "name": self.name,
            "slug": self.slug,
            "description": self.description,
            "is_active": self.is_active,
        }


# ─── product ─────────────────────────────────────────────────────────────────
# status replaces is_active — more expressive and matches CMS spec.
# Added: era, material, year, condition, badge, is_unique, sold_at, archive_at.

class ProductStatus(sa.types.TypeDecorator):
    impl = sa.String
    cache_ok = True
    VALID = {"live", "draft", "sold", "archived"}

class ProductCondition(sa.types.TypeDecorator):
    impl = sa.String
    cache_ok = True
    VALID = {"Excellent", "Very Good", "Good", "Restored"}

class ProductBadge(sa.types.TypeDecorator):
    impl = sa.String
    cache_ok = True
    VALID = {"New In", "Last One", "Sale"}


class Product(db.Model):
    __tablename__ = "products"

    id = uuid_pk()
    name = db.Column(db.String(255), nullable=False)
    slug = db.Column(db.String(255), unique=True, nullable=False)
    description = db.Column(db.Text, nullable=True)

    # Category FK
    category_id = db.Column(UUID(as_uuid=True), db.ForeignKey("categories.id"), nullable=True)

    # Product character fields (from CMS spec)
    era = db.Column(db.String(100), nullable=True)         # e.g. "1962" or "1960s"
    material = db.Column(db.String(255), nullable=True)    # e.g. "Solid Teak"
    year = db.Column(db.Integer, nullable=True)            # manufacture year
    condition = db.Column(db.String(50), nullable=True)    # Excellent | Very Good | Good | Restored

    # Display flags
    status = db.Column(db.String(20), default="draft", nullable=False)  # live|draft|sold|archived
    badge = db.Column(db.String(20), nullable=True)        # New In | Last One | Sale
    is_featured = db.Column(db.Boolean, default=False)
    is_unique = db.Column(db.Boolean, default=False)       # appears in 2 spots on homepage

    # Instagram
    instagram_post_id = db.Column(db.String(255), nullable=True)
    instagram_post_url = db.Column(db.String(500), nullable=True)

    # Lifecycle timestamps
    sold_at = db.Column(db.DateTime(timezone=True), nullable=True)
    archive_at = db.Column(db.DateTime(timezone=True), nullable=True)  # sold_at + 30 days
    created_at = db.Column(db.DateTime(timezone=True), default=now_utc)
    updated_at = db.Column(db.DateTime(timezone=True), default=now_utc, onupdate=now_utc)

    # Relationships
    category = db.relationship("Category", back_populates="products")
    variants = db.relationship("ProductVariant", back_populates="product", cascade="all, delete-orphan")
    images = db.relationship(
        "ProductImage", back_populates="product",
        cascade="all, delete-orphan",
        order_by="ProductImage.sort_order"
    )
    reviews = db.relationship("Review", back_populates="product", cascade="all, delete-orphan")
    collections = db.relationship("Collection", secondary=product_collections, back_populates="products")

    @property
    def primary_image(self):
        for img in self.images:
            if img.is_primary:
                return img
        return self.images[0] if self.images else None

    def to_dict(self, include_variants=True, include_images=True, include_reviews=False):
        d = {
            "id": str(self.id),
            "name": self.name,
            "slug": self.slug,
            "description": self.description,
            "era": self.era,
            "material": self.material,
            "year": self.year,
            "condition": self.condition,
            "status": self.status,
            "badge": self.badge,
            "is_featured": self.is_featured,
            "is_unique": self.is_unique,
            "category": self.category.to_dict() if self.category else None,
            "instagram_post_id": self.instagram_post_id,
            "instagram_post_url": self.instagram_post_url,
            "sold_at": self.sold_at.isoformat() if self.sold_at else None,
            "archive_at": self.archive_at.isoformat() if self.archive_at else None,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
        if include_variants:
            d["variants"] = [v.to_dict() for v in self.variants]
        if include_images:
            d["images"] = [img.to_dict() for img in self.images]
            d["primary_image"] = self.primary_image.to_dict() if self.primary_image else None
        if include_reviews:
            d["reviews"] = [r.to_dict() for r in self.reviews if r.is_approved]
        return d


# ─── product variant ─────────────────────────────────────────────────────────

class ProductVariant(db.Model):
    __tablename__ = "product_variants"

    id = uuid_pk()
    product_id = db.Column(UUID(as_uuid=True), db.ForeignKey("products.id"), nullable=False)
    name = db.Column(db.String(255), nullable=True)        # e.g. "Walnut / Large"
    price = db.Column(db.Numeric(10, 2), nullable=False)
    sale_price = db.Column(db.Numeric(10, 2), nullable=True)
    sku = db.Column(db.String(100), unique=True, nullable=True)
    stock_qty = db.Column(db.Integer, default=1)
    is_available = db.Column(db.Boolean, default=True)

    product = db.relationship("Product", back_populates="variants")
    images = db.relationship("ProductImage", back_populates="variant")

    @property
    def effective_price(self):
        return float(self.sale_price) if self.sale_price else float(self.price)

    @property
    def on_sale(self):
        return self.sale_price is not None and self.sale_price < self.price

    def to_dict(self):
        return {
            "id": str(self.id),
            "product_id": str(self.product_id),
            "name": self.name,
            "price": float(self.price),
            "sale_price": float(self.sale_price) if self.sale_price else None,
            "effective_price": self.effective_price,
            "on_sale": self.on_sale,
            "sku": self.sku,
            "stock_qty": self.stock_qty,
            "is_available": self.is_available,
        }


# ─── product image ───────────────────────────────────────────────────────────

class ProductImage(db.Model):
    __tablename__ = "product_images"

    id = uuid_pk()
    product_id = db.Column(UUID(as_uuid=True), db.ForeignKey("products.id"), nullable=False)
    variant_id = db.Column(UUID(as_uuid=True), db.ForeignKey("product_variants.id"), nullable=True)
    url = db.Column(db.String(500), nullable=True)  # legacy / fallback
    data = db.Column(db.LargeBinary, nullable=True)  # image bytes stored in PostgreSQL
    content_type = db.Column(db.String(100), nullable=True)  # e.g. image/jpeg
    filename = db.Column(db.String(255), nullable=True)
    alt_text = db.Column(db.String(255), nullable=True)
    sort_order = db.Column(db.Integer, default=0)
    is_primary = db.Column(db.Boolean, default=False)

    product = db.relationship("Product", back_populates="images")
    variant = db.relationship("ProductVariant", back_populates="images")

    @property
    def image_url(self):
        """Return the full serving URL for this image."""
        if self.data is not None:
            from flask import request as _req
            try:
                base = _req.host_url.rstrip("/")
            except RuntimeError:
                base = ""
            return f"{base}/api/images/{self.id}"
        return self.url

    def to_dict(self):
        return {
            "id": str(self.id),
            "product_id": str(self.product_id),
            "variant_id": str(self.variant_id) if self.variant_id else None,
            "url": self.image_url,
            "alt_text": self.alt_text,
            "sort_order": self.sort_order,
            "is_primary": self.is_primary,
        }


# ─── cart ────────────────────────────────────────────────────────────────────

class Cart(db.Model):
    __tablename__ = "carts"

    id = uuid_pk()
    session_id = db.Column(db.String(255), unique=True, nullable=False)
    expires_at = db.Column(db.DateTime(timezone=True), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=now_utc)
    updated_at = db.Column(db.DateTime(timezone=True), default=now_utc, onupdate=now_utc)

    items = db.relationship("CartItem", back_populates="cart", cascade="all, delete-orphan")

    @property
    def is_expired(self):
        return datetime.now(timezone.utc) > self.expires_at

    def to_dict(self):
        return {
            "id": str(self.id),
            "session_id": self.session_id,
            "expires_at": self.expires_at.isoformat(),
            "items": [item.to_dict() for item in self.items],
            "total": sum(
                float(item.variant.effective_price) * item.quantity
                for item in self.items
                if item.variant
            ),
        }


class CartItem(db.Model):
    __tablename__ = "cart_items"

    id = uuid_pk()
    cart_id = db.Column(UUID(as_uuid=True), db.ForeignKey("carts.id", ondelete="CASCADE"), nullable=False)
    product_variant_id = db.Column(UUID(as_uuid=True), db.ForeignKey("product_variants.id"), nullable=False)
    quantity = db.Column(db.Integer, default=1, nullable=False)
    added_at = db.Column(db.DateTime(timezone=True), default=now_utc)

    cart = db.relationship("Cart", back_populates="items")
    variant = db.relationship("ProductVariant")

    def to_dict(self):
        v = self.variant
        p = v.product if v else None
        return {
            "id": str(self.id),
            "quantity": self.quantity,
            "variant": v.to_dict() if v else None,
            "product": {
                "id": str(p.id),
                "name": p.name,
                "slug": p.slug,
                "primary_image": p.primary_image.to_dict() if p and p.primary_image else None,
            } if p else None,
            "line_total": float(v.effective_price) * self.quantity if v else 0,
        }


# ─── order ───────────────────────────────────────────────────────────────────
# Status reconciled: CMS 'confirmed' added, blueprint 'paid' kept.
# Fulfillment: collection | shipping (renamed from delivery to match CMS)

class Order(db.Model):
    __tablename__ = "orders"

    id = uuid_pk()
    order_number = db.Column(db.String(32), unique=True, nullable=False)

    # Status: pending → confirmed → paid → shipped/collected → delivered/cancelled
    status = db.Column(
        db.String(20),
        default="pending",
        nullable=False
    )  # pending|confirmed|paid|shipped|collected|delivered|cancelled

    fulfillment_type = db.Column(db.String(20), nullable=False)  # collection | shipping

    total_amount = db.Column(db.Numeric(10, 2), nullable=False)

    # Customer details stored in jsonb (no user account)
    billing_address = db.Column(JSONB, nullable=False)
    # { name, email, phone, address_line1, city, province, postal_code }

    shipping_address = db.Column(JSONB, nullable=True)   # only if fulfillment_type = shipping
    collection_address = db.Column(JSONB, nullable=True) # only if fulfillment_type = collection
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), default=now_utc)

    items = db.relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")
    payments = db.relationship("Payment", back_populates="order", cascade="all, delete-orphan")

    def to_dict(self, admin=False):
        d = {
            "id": str(self.id),
            "order_number": self.order_number,
            "status": self.status,
            "fulfillment_type": self.fulfillment_type,
            "total_amount": float(self.total_amount),
            "notes": self.notes,
            "created_at": self.created_at.isoformat(),
            "items": [item.to_dict() for item in self.items],
        }
        if admin:
            d["billing_address"] = self.billing_address
            d["shipping_address"] = self.shipping_address
            d["collection_address"] = self.collection_address
            d["payments"] = [p.to_dict() for p in self.payments]
        else:
            # Public: only non-sensitive fields
            d["customer_name"] = self.billing_address.get("name") if self.billing_address else None
            d["fulfillment_address"] = self.shipping_address or self.collection_address
        return d


class OrderItem(db.Model):
    __tablename__ = "order_items"

    id = uuid_pk()
    order_id = db.Column(UUID(as_uuid=True), db.ForeignKey("orders.id"), nullable=False)
    product_variant_id = db.Column(UUID(as_uuid=True), db.ForeignKey("product_variants.id"), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    price_at_purchase = db.Column(db.Numeric(10, 2), nullable=False)  # locked at order time
    product_snapshot = db.Column(JSONB, nullable=True)  # name + variant at time of order

    order = db.relationship("Order", back_populates="items")
    variant = db.relationship("ProductVariant")

    def to_dict(self):
        return {
            "id": str(self.id),
            "quantity": self.quantity,
            "price_at_purchase": float(self.price_at_purchase),
            "line_total": float(self.price_at_purchase) * self.quantity,
            "product_snapshot": self.product_snapshot,
        }


# ─── payment ─────────────────────────────────────────────────────────────────

class Payment(db.Model):
    __tablename__ = "payments"

    id = uuid_pk()
    order_id = db.Column(UUID(as_uuid=True), db.ForeignKey("orders.id"), nullable=False)
    method = db.Column(db.String(20), nullable=False)   # payfast | yoco
    status = db.Column(db.String(20), nullable=False, default="initiated")  # initiated|completed|failed|cancelled
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    transaction_id = db.Column(db.String(255), nullable=True)
    paid_at = db.Column(db.DateTime(timezone=True), nullable=True)
    raw_webhook = db.Column(JSONB, nullable=True)  # raw payload for debugging

    order = db.relationship("Order", back_populates="payments")

    def to_dict(self):
        return {
            "id": str(self.id),
            "method": self.method,
            "status": self.status,
            "amount": float(self.amount),
            "transaction_id": self.transaction_id,
            "paid_at": self.paid_at.isoformat() if self.paid_at else None,
        }


# ─── review ──────────────────────────────────────────────────────────────────

class Review(db.Model):
    __tablename__ = "reviews"

    id = uuid_pk()
    product_id = db.Column(UUID(as_uuid=True), db.ForeignKey("products.id"), nullable=False)
    reviewer_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(255), nullable=True)
    rating = db.Column(db.Integer, nullable=False)  # 1-5
    comment = db.Column(db.Text, nullable=True)
    is_approved = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime(timezone=True), default=now_utc)
    updated_at = db.Column(db.DateTime(timezone=True), default=now_utc, onupdate=now_utc)

    product = db.relationship("Product", back_populates="reviews")

    def to_dict(self):
        return {
            "id": str(self.id),
            "product_id": str(self.product_id) if self.product_id else None,
            "reviewer_name": self.reviewer_name,
            "email": self.email,
            "rating": self.rating,
            "comment": self.comment,
            "is_approved": self.is_approved,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


# ─── subscriber ──────────────────────────────────────────────────────────────

class Subscriber(db.Model):
    __tablename__ = "subscribers"

    id = uuid_pk()
    email = db.Column(db.String(255), unique=True, nullable=False)
    first_name = db.Column(db.String(100), nullable=True)
    last_name = db.Column(db.String(100), nullable=True)
    phone = db.Column(db.String(30), nullable=True)
    area = db.Column(db.String(100), nullable=True)
    source = db.Column(db.String(50), default="footer")  # footer|popup|checkout
    is_active = db.Column(db.Boolean, default=True)
    subscribed_at = db.Column(db.DateTime(timezone=True), default=now_utc)
    created_at = db.Column(db.DateTime(timezone=True), default=now_utc)
    updated_at = db.Column(db.DateTime(timezone=True), default=now_utc, onupdate=now_utc)

    def to_dict(self):
        return {
            "id": str(self.id),
            "email": self.email,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "phone": self.phone,
            "area": self.area,
            "source": self.source,
            "is_active": self.is_active,
            "subscribed_at": self.subscribed_at.isoformat(),
        }


# ─── upcoming item ───────────────────────────────────────────────────────────

class UpcomingItem(db.Model):
    __tablename__ = "upcoming_items"

    id = uuid_pk()
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=True)
    estimated_price = db.Column(db.Numeric(10, 2), nullable=True)
    status = db.Column(db.String(30), default="coming-soon")
    # coming-soon | sourced | in-restoration | expected-this-week
    notify_count = db.Column(db.Integer, default=0)
    sort_order = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime(timezone=True), default=now_utc)
    updated_at = db.Column(db.DateTime(timezone=True), default=now_utc, onupdate=now_utc)

    def to_dict(self):
        return {
            "id": str(self.id),
            "name": self.name,
            "description": self.description,
            "estimated_price": float(self.estimated_price) if self.estimated_price else None,
            "status": self.status,
            "notify_count": self.notify_count,
            "sort_order": self.sort_order,
            "created_at": self.created_at.isoformat(),
        }


# ─── enquiry ─────────────────────────────────────────────────────────────────

class Enquiry(db.Model):
    __tablename__ = "enquiries"

    id = uuid_pk()
    name = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(255), nullable=False)
    phone = db.Column(db.String(20), nullable=True)
    message = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(50), default="unread")  # unread | read | replied
    created_at = db.Column(db.DateTime(timezone=True), default=now_utc)
    updated_at = db.Column(db.DateTime(timezone=True), default=now_utc, onupdate=now_utc)

    def to_dict(self):
        return {
            "id": str(self.id),
            "name": self.name,
            "email": self.email,
            "phone": self.phone,
            "message": self.message,
            "status": self.status,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
