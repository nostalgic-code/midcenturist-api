so you are senior backend enginner and you have been tasked with implementing the following 



Create the Flask project directory structure

Script

requirements.txt with all Flask dependencies
requirements.txt

Flask app config with dev/production classes
config.py

Flask extensions — db, limiter, cors, talisman instantiated here to avoid circular imports
extensions.py

Flask app factory — creates and configures the app
__init__.py

All SQLAlchemy models — products, variants, images, categories, collections, carts, orders, payments, subscribers, reviews. Reconciled with CMS spec fields.
__init__.py

Security utilities — admin token decorator, HMAC helpers
security.py

Input validators — email, phone, order payload, product payload
validators.py

Public products routes — list, detail by slug, search
products.py

Public categories and collections routes
categories.py

Cart routes — create, get, add item, update quantity, clear
cart.py

Orders routes — create from cart (guest checkout), public status check
orders.py

Payment routes — PayFast initiate + ITN webhook, Yoco initiate + webhook
payments.py

Newsletter subscribe + public reviews routes
newsletter.py

Admin products routes — full CRUD + image upload + mark sold
products.py

Admin orders + categories + instagram + reviews routes
__init__.py


and here is the code for that 

requirements.txt


flask==3.0.3
flask-sqlalchemy==3.1.1
flask-migrate==4.0.7
flask-cors==4.0.1
flask-wtf==1.2.1
flask-limiter==3.7.0
flask-talisman==1.1.0
psycopg2-binary==2.9.9
sqlalchemy==2.0.31
alembic==1.13.2
python-dotenv==1.0.1
marshmallow==3.21.3
requests==2.32.3
cloudinary==1.40.0
resend==2.3.0
gunicorn==22.0.0


config.py 


import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-change-in-production")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    WTF_CSRF_ENABLED = True
    ADMIN_JWT_SECRET = os.environ.get("ADMIN_JWT_SECRET", "admin-secret-change-in-production")

    # Payment gateways
    PAYFAST_MERCHANT_ID = os.environ.get("PAYFAST_MERCHANT_ID", "")
    PAYFAST_MERCHANT_KEY = os.environ.get("PAYFAST_MERCHANT_KEY", "")
    PAYFAST_PASSPHRASE = os.environ.get("PAYFAST_PASSPHRASE", "")
    PAYFAST_SANDBOX = os.environ.get("PAYFAST_SANDBOX", "true").lower() == "true"

    YOCO_SECRET_KEY = os.environ.get("YOCO_SECRET_KEY", "")
    YOCO_SANDBOX = os.environ.get("YOCO_SANDBOX", "true").lower() == "true"

    # Instagram / Meta Graph API
    INSTAGRAM_ACCESS_TOKEN = os.environ.get("INSTAGRAM_ACCESS_TOKEN", "")
    INSTAGRAM_BUSINESS_ACCOUNT_ID = os.environ.get("INSTAGRAM_BUSINESS_ACCOUNT_ID", "")

    # Email (Resend)
    RESEND_API_KEY = os.environ.get("RESEND_API_KEY", "")
    CLIENT_EMAIL = os.environ.get("CLIENT_EMAIL", "")
    FROM_EMAIL = os.environ.get("FROM_EMAIL", "noreply@midcenturist.co.za")

    # Image storage (Cloudinary)
    CLOUDINARY_URL = os.environ.get("CLOUDINARY_URL", "")

    # CORS
    ALLOWED_ORIGINS = os.environ.get(
        "ALLOWED_ORIGINS",
        "http://localhost:3000,http://localhost:3001"
    ).split(",")

    # Rate limiting storage (use Redis in production)
    RATELIMIT_STORAGE_URL = os.environ.get("REDIS_URL", "memory://")


class DevelopmentConfig(Config):
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL",
        "postgresql://postgres:postgres@localhost/midcenturist_dev"
    )
    WTF_CSRF_ENABLED = False  # disable in dev for easier API testing


class ProductionConfig(Config):
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL", "")

    # Render provides DATABASE_URL with postgres:// prefix — SQLAlchemy needs postgresql://
    @classmethod
    def init_app(cls, app):
        db_url = cls.SQLALCHEMY_DATABASE_URI
        if db_url and db_url.startswith("postgres://"):
            cls.SQLALCHEMY_DATABASE_URI = db_url.replace("postgres://", "postgresql://", 1)


config = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig,
}



extensions.py

from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_talisman import Talisman

db = SQLAlchemy()
migrate = Migrate()
cors = CORS()
limiter = Limiter(key_func=get_remote_address)
talisman = Talisman()

__init__.py

from flask import Flask
from app.config import config
from app.extensions import db, migrate, cors, limiter, talisman
import os


def create_app(config_name: str = None) -> Flask:
    if config_name is None:
        config_name = os.environ.get("FLASK_ENV", "development")

    app = Flask(__name__)
    app.config.from_object(config[config_name])

    # Call init_app for production fixes (postgres:// → postgresql://)
    if hasattr(config[config_name], "init_app"):
        config[config_name].init_app(app)

    # Extensions
    db.init_app(app)
    migrate.init_app(app, db)

    cors.init_app(
        app,
        resources={r"/api/*": {"origins": app.config["ALLOWED_ORIGINS"]}},
        supports_credentials=True,
    )

    limiter.init_app(app)

    # Security headers — relaxed for API (no CSP needed, no HTML responses)
    talisman.init_app(
        app,
        force_https=not app.debug,
        content_security_policy=False,
        strict_transport_security=not app.debug,
        referrer_policy="strict-origin-when-cross-origin",
    )

    # Register blueprints
    from app.routes.products import products_bp
    from app.routes.categories import categories_bp
    from app.routes.cart import cart_bp
    from app.routes.orders import orders_bp
    from app.routes.payments import payments_bp
    from app.routes.newsletter import newsletter_bp
    from app.routes.reviews import reviews_bp
    from app.routes.admin.products import admin_products_bp
    from app.routes.admin.orders import admin_orders_bp
    from app.routes.admin.categories import admin_categories_bp
    from app.routes.admin.instagram import admin_instagram_bp
    from app.routes.admin.reviews import admin_reviews_bp

    app.register_blueprint(products_bp, url_prefix="/api")
    app.register_blueprint(categories_bp, url_prefix="/api")
    app.register_blueprint(cart_bp, url_prefix="/api")
    app.register_blueprint(orders_bp, url_prefix="/api")
    app.register_blueprint(payments_bp, url_prefix="/api/payments")
    app.register_blueprint(newsletter_bp, url_prefix="/api")
    app.register_blueprint(reviews_bp, url_prefix="/api")
    app.register_blueprint(admin_products_bp, url_prefix="/api/admin")
    app.register_blueprint(admin_orders_bp, url_prefix="/api/admin")
    app.register_blueprint(admin_categories_bp, url_prefix="/api/admin")
    app.register_blueprint(admin_instagram_bp, url_prefix="/api/admin")
    app.register_blueprint(admin_reviews_bp, url_prefix="/api/admin")

    # Health check
    @app.get("/api/health")
    def health():
        return {"status": "ok", "env": config_name}

    return app



    __init__.py

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
    url = db.Column(db.String(500), nullable=False)
    alt_text = db.Column(db.String(255), nullable=True)
    sort_order = db.Column(db.Integer, default=0)
    is_primary = db.Column(db.Boolean, default=False)

    product = db.relationship("Product", back_populates="images")
    variant = db.relationship("ProductVariant", back_populates="images")

    def to_dict(self):
        return {
            "id": str(self.id),
            "product_id": str(self.product_id),
            "variant_id": str(self.variant_id) if self.variant_id else None,
            "url": self.url,
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
    rating = db.Column(db.Integer, nullable=False)  # 1-5
    comment = db.Column(db.Text, nullable=True)
    is_approved = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime(timezone=True), default=now_utc)

    product = db.relationship("Product", back_populates="reviews")

    def to_dict(self):
        return {
            "id": str(self.id),
            "reviewer_name": self.reviewer_name,
            "rating": self.rating,
            "comment": self.comment,
            "created_at": self.created_at.isoformat(),
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



security.py

import hmac
import hashlib
import jwt
from functools import wraps
from flask import request, jsonify, current_app
from datetime import datetime, timezone, timedelta


# ─── Admin JWT auth ──────────────────────────────────────────────────────────

def require_admin(f):
    """Decorator that validates the Bearer token on admin routes."""
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.headers.get("Authorization", "")
        if not auth.startswith("Bearer "):
            return jsonify({"error": "Missing authorisation header"}), 401

        token = auth.split(" ", 1)[1]
        try:
            jwt.decode(
                token,
                current_app.config["ADMIN_JWT_SECRET"],
                algorithms=["HS256"],
            )
        except jwt.ExpiredSignatureError:
            return jsonify({"error": "Token expired"}), 401
        except jwt.InvalidTokenError:
            return jsonify({"error": "Invalid token"}), 401

        return f(*args, **kwargs)
    return decorated


def generate_admin_token(email: str, expires_hours: int = 24) -> str:
    """Used by login endpoint to issue a JWT."""
    payload = {
        "sub": email,
        "iat": datetime.now(timezone.utc),
        "exp": datetime.now(timezone.utc) + timedelta(hours=expires_hours),
    }
    return jwt.encode(
        payload,
        current_app.config["ADMIN_JWT_SECRET"],
        algorithm="HS256",
    )


# ─── PayFast signature ───────────────────────────────────────────────────────

def generate_payfast_signature(data: dict, passphrase: str = None) -> str:
    """Generate the MD5 signature required by PayFast."""
    # Sort keys, build query string
    parts = []
    for key in sorted(data.keys()):
        val = str(data[key]).strip()
        if val:
            parts.append(f"{key}={val}")

    query = "&".join(parts)

    if passphrase:
        query += f"&passphrase={passphrase}"

    return hashlib.md5(query.encode()).hexdigest()


def verify_payfast_itn(post_data: dict, passphrase: str = None) -> bool:
    """Verify the signature on an incoming PayFast ITN (Instant Transaction Notification)."""
    received_sig = post_data.pop("signature", None)
    if not received_sig:
        return False

    expected_sig = generate_payfast_signature(post_data.copy(), passphrase)
    post_data["signature"] = received_sig  # restore
    return hmac.compare_digest(received_sig.lower(), expected_sig.lower())



    validators.py


    import re
from typing import Any


EMAIL_RE = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")
PHONE_RE = re.compile(r"^[\d\s\+\-\(\)]{7,20}$")

VALID_PRODUCT_STATUSES = {"live", "draft", "sold", "archived"}
VALID_ORDER_STATUSES = {"pending", "confirmed", "paid", "shipped", "collected", "delivered", "cancelled"}
VALID_FULFILLMENT_TYPES = {"collection", "shipping"}
VALID_CONDITIONS = {"Excellent", "Very Good", "Good", "Restored"}
VALID_BADGES = {"New In", "Last One", "Sale"}
VALID_UPCOMING_STATUSES = {"coming-soon", "sourced", "in-restoration", "expected-this-week"}


def is_valid_email(email: str) -> bool:
    return bool(EMAIL_RE.match(email.strip())) if email else False


def is_valid_phone(phone: str) -> bool:
    return bool(PHONE_RE.match(phone.strip())) if phone else False


def validate_checkout(data: dict) -> list[str]:
    """Validate checkout / order creation payload. Returns list of error strings."""
    errors = []

    billing = data.get("billing_address", {})
    if not billing.get("name"):
        errors.append("billing_address.name is required")
    if not is_valid_email(billing.get("email", "")):
        errors.append("billing_address.email is invalid")
    if not is_valid_phone(billing.get("phone", "")):
        errors.append("billing_address.phone is invalid")

    ft = data.get("fulfillment_type", "")
    if ft not in VALID_FULFILLMENT_TYPES:
        errors.append(f"fulfillment_type must be one of: {', '.join(VALID_FULFILLMENT_TYPES)}")

    if ft == "shipping":
        sa = data.get("shipping_address", {})
        if not sa.get("address_line1"):
            errors.append("shipping_address.address_line1 is required for shipping orders")
        if not sa.get("city"):
            errors.append("shipping_address.city is required for shipping orders")

    if not data.get("session_id"):
        errors.append("session_id is required")

    return errors


def validate_product(data: dict, is_update: bool = False) -> list[str]:
    """Validate admin product create/update payload."""
    errors = []

    if not is_update:
        if not data.get("name"):
            errors.append("name is required")

    status = data.get("status")
    if status and status not in VALID_PRODUCT_STATUSES:
        errors.append(f"status must be one of: {', '.join(VALID_PRODUCT_STATUSES)}")

    condition = data.get("condition")
    if condition and condition not in VALID_CONDITIONS:
        errors.append(f"condition must be one of: {', '.join(VALID_CONDITIONS)}")

    badge = data.get("badge")
    if badge and badge not in VALID_BADGES:
        errors.append(f"badge must be one of: {', '.join(VALID_BADGES)}")

    price = data.get("price")
    if price is not None:
        try:
            p = float(price)
            if p < 0:
                errors.append("price cannot be negative")
        except (ValueError, TypeError):
            errors.append("price must be a number")

    return errors


def validate_review(data: dict) -> list[str]:
    errors = []
    if not data.get("reviewer_name"):
        errors.append("reviewer_name is required")
    rating = data.get("rating")
    if rating is None or not isinstance(rating, int) or not (1 <= rating <= 5):
        errors.append("rating must be an integer between 1 and 5")
    return errors


def sanitise_string(val: Any, max_length: int = 500) -> str | None:
    if val is None:
        return None
    return str(val).strip()[:max_length]




    products.py


    from flask import Blueprint, request, jsonify
from app.extensions import db, limiter
from app.models import Product, Category, Collection
from sqlalchemy import or_, func

products_bp = Blueprint("products", __name__)


@products_bp.get("/products")
@limiter.limit("60 per minute")
def list_products():
    """
    GET /api/products
    Query params:
      category=slug
      collection=slug
      status=live (default)
      featured=true
      badge=New In|Last One|Sale
      page=1
      limit=24
    """
    q = Product.query

    # Default to live products only on public endpoint
    status = request.args.get("status", "live")
    q = q.filter(Product.status == status)

    category_slug = request.args.get("category")
    if category_slug:
        cat = Category.query.filter_by(slug=category_slug).first()
        if cat:
            q = q.filter(Product.category_id == cat.id)
        else:
            return jsonify({"products": [], "total": 0})

    collection_slug = request.args.get("collection")
    if collection_slug:
        col = Collection.query.filter_by(slug=collection_slug).first()
        if col:
            q = q.filter(Product.collections.any(id=col.id))

    if request.args.get("featured") == "true":
        q = q.filter(Product.is_featured == True)

    badge = request.args.get("badge")
    if badge:
        q = q.filter(Product.badge == badge)

    try:
        page = max(1, int(request.args.get("page", 1)))
        limit = min(48, max(1, int(request.args.get("limit", 24))))
    except ValueError:
        page, limit = 1, 24

    total = q.count()
    products = q.order_by(Product.created_at.desc()).offset((page - 1) * limit).limit(limit).all()

    return jsonify({
        "products": [p.to_dict(include_reviews=False) for p in products],
        "total": total,
        "page": page,
        "limit": limit,
        "pages": (total + limit - 1) // limit,
    })


@products_bp.get("/products/search")
@limiter.limit("30 per minute")
def search_products():
    """GET /api/products/search?q=teak+sideboard"""
    q_str = request.args.get("q", "").strip()
    if not q_str or len(q_str) < 2:
        return jsonify({"products": [], "total": 0})

    # PostgreSQL full-text search using ILIKE for simplicity
    # Upgrade to tsvector index in production if needed
    search = f"%{q_str}%"
    results = Product.query.filter(
        Product.status == "live",
        or_(
            Product.name.ilike(search),
            Product.description.ilike(search),
            Product.material.ilike(search),
            Product.era.ilike(search),
        )
    ).limit(20).all()

    return jsonify({
        "products": [p.to_dict() for p in results],
        "total": len(results),
        "query": q_str,
    })


@products_bp.get("/products/<string:slug>")
@limiter.limit("120 per minute")
def get_product(slug: str):
    """GET /api/products/:slug"""
    product = Product.query.filter_by(slug=slug).first()

    if not product:
        return jsonify({"error": "Product not found"}), 404

    if product.status == "archived":
        return jsonify({"error": "Product no longer available"}), 410

    return jsonify(product.to_dict(include_reviews=True))



 categories/.py


 from flask import Blueprint, jsonify
from app.extensions import limiter
from app.models import Category, Collection, Product

categories_bp = Blueprint("categories", __name__)


@categories_bp.get("/categories")
@limiter.limit("60 per minute")
def list_categories():
    """GET /api/categories — full tree with product counts."""
    top_level = Category.query.filter_by(parent_id=None).all()

    def build_node(cat):
        count = Product.query.filter_by(category_id=cat.id, status="live").count()
        node = cat.to_dict()
        node["product_count"] = count
        node["children"] = [build_node(c) for c in cat.children]
        return node

    return jsonify({"categories": [build_node(c) for c in top_level]})


@categories_bp.get("/categories/<string:slug>/products")
@limiter.limit("60 per minute")
def category_products(slug: str):
    """GET /api/categories/:slug/products"""
    cat = Category.query.filter_by(slug=slug).first()
    if not cat:
        return jsonify({"error": "Category not found"}), 404

    # Include child categories
    cat_ids = [cat.id] + [c.id for c in cat.children]
    products = Product.query.filter(
        Product.category_id.in_(cat_ids),
        Product.status == "live"
    ).order_by(Product.created_at.desc()).all()

    return jsonify({
        "category": cat.to_dict(),
        "products": [p.to_dict() for p in products],
        "total": len(products),
    })


@categories_bp.get("/collections")
@limiter.limit("60 per minute")
def list_collections():
    """GET /api/collections"""
    collections = Collection.query.filter_by(is_active=True).all()
    return jsonify({"collections": [c.to_dict() for c in collections]})


@categories_bp.get("/collections/<string:slug>/products")
@limiter.limit("60 per minute")
def collection_products(slug: str):
    """GET /api/collections/:slug/products"""
    col = Collection.query.filter_by(slug=slug, is_active=True).first()
    if not col:
        return jsonify({"error": "Collection not found"}), 404

    products = [p for p in col.products if p.status == "live"]

    return jsonify({
        "collection": col.to_dict(),
        "products": [p.to_dict() for p in products],
        "total": len(products),
    })




    cart.py


    import uuid
from datetime import datetime, timezone, timedelta
from flask import Blueprint, request, jsonify
from app.extensions import db, limiter
from app.models import Cart, CartItem, ProductVariant

cart_bp = Blueprint("cart", __name__)

CART_TTL_DAYS = 7


@cart_bp.post("/cart")
@limiter.limit("10 per minute")
def create_cart():
    """POST /api/cart — create a new cart, return session_id."""
    session_id = str(uuid.uuid4())
    cart = Cart(
        session_id=session_id,
        expires_at=datetime.now(timezone.utc) + timedelta(days=CART_TTL_DAYS),
    )
    db.session.add(cart)
    db.session.commit()
    return jsonify({"session_id": session_id, "cart": cart.to_dict()}), 201


@cart_bp.get("/cart/<string:session_id>")
@limiter.limit("60 per minute")
def get_cart(session_id: str):
    """GET /api/cart/:sessionId"""
    cart = Cart.query.filter_by(session_id=session_id).first()
    if not cart:
        return jsonify({"error": "Cart not found"}), 404
    if cart.is_expired:
        return jsonify({"error": "Cart has expired"}), 410
    return jsonify(cart.to_dict())


@cart_bp.post("/cart/<string:session_id>/items")
@limiter.limit("20 per minute")
def add_item(session_id: str):
    """POST /api/cart/:sessionId/items — add a product variant to cart."""
    cart = _get_active_cart(session_id)
    if isinstance(cart, tuple):
        return cart  # error response

    data = request.get_json(silent=True) or {}
    variant_id = data.get("product_variant_id")
    quantity = int(data.get("quantity", 1))

    if not variant_id or quantity < 1:
        return jsonify({"error": "product_variant_id and quantity >= 1 are required"}), 400

    variant = ProductVariant.query.filter_by(id=variant_id, is_available=True).first()
    if not variant:
        return jsonify({"error": "Product variant not available"}), 404

    # Check stock
    if variant.stock_qty < quantity:
        return jsonify({"error": "Insufficient stock", "available": variant.stock_qty}), 409

    # Check if already in cart — increment quantity
    existing = CartItem.query.filter_by(cart_id=cart.id, product_variant_id=variant_id).first()
    if existing:
        existing.quantity = min(existing.quantity + quantity, variant.stock_qty)
    else:
        item = CartItem(
            cart_id=cart.id,
            product_variant_id=variant_id,
            quantity=quantity,
        )
        db.session.add(item)

    db.session.commit()
    return jsonify(cart.to_dict()), 200


@cart_bp.put("/cart/<string:session_id>/items/<string:item_id>")
@limiter.limit("30 per minute")
def update_item(session_id: str, item_id: str):
    """PUT /api/cart/:sessionId/items/:itemId — update qty (0 = remove)."""
    cart = _get_active_cart(session_id)
    if isinstance(cart, tuple):
        return cart

    data = request.get_json(silent=True) or {}
    quantity = int(data.get("quantity", 1))

    item = CartItem.query.filter_by(id=item_id, cart_id=cart.id).first()
    if not item:
        return jsonify({"error": "Item not found in cart"}), 404

    if quantity <= 0:
        db.session.delete(item)
    else:
        item.quantity = quantity

    db.session.commit()
    return jsonify(cart.to_dict())


@cart_bp.delete("/cart/<string:session_id>")
@limiter.limit("10 per minute")
def clear_cart(session_id: str):
    """DELETE /api/cart/:sessionId — clear all items (called after successful order)."""
    cart = Cart.query.filter_by(session_id=session_id).first()
    if not cart:
        return jsonify({"error": "Cart not found"}), 404

    for item in cart.items:
        db.session.delete(item)
    db.session.commit()
    return jsonify({"message": "Cart cleared"})


def _get_active_cart(session_id: str):
    cart = Cart.query.filter_by(session_id=session_id).first()
    if not cart:
        return jsonify({"error": "Cart not found"}), 404
    if cart.is_expired:
        return jsonify({"error": "Cart has expired — please start a new cart"}), 410
    return cart



     orders.py

     import uuid
from datetime import datetime, timezone, timedelta
from flask import Blueprint, request, jsonify, current_app
from app.extensions import db, limiter
from app.models import Cart, Order, OrderItem, Product, ProductVariant
from app.utils.validators import validate_checkout

orders_bp = Blueprint("orders", __name__)


def _generate_order_number() -> str:
    today = datetime.now(timezone.utc).strftime("%Y%m%d")
    short_id = str(uuid.uuid4()).replace("-", "")[:6].upper()
    return f"MCR-{today}-{short_id}"


@orders_bp.post("/orders")
@limiter.limit("3 per minute")
def create_order():
    """
    POST /api/orders
    Body: {
      session_id,
      fulfillment_type: "collection" | "shipping",
      billing_address: { name, email, phone, address_line1?, city?, province?, postal_code? },
      shipping_address?: { ... },
      collection_address?: { ... },
      notes?: string
    }
    """
    data = request.get_json(silent=True) or {}

    errors = validate_checkout(data)
    if errors:
        return jsonify({"errors": errors}), 422

    session_id = data["session_id"]
    cart = Cart.query.filter_by(session_id=session_id).first()
    if not cart:
        return jsonify({"error": "Cart not found"}), 404
    if cart.is_expired:
        return jsonify({"error": "Cart has expired"}), 410
    if not cart.items:
        return jsonify({"error": "Cart is empty"}), 400

    # Lock prices and validate stock atomically
    order_items = []
    total = 0

    for cart_item in cart.items:
        variant = ProductVariant.query.with_for_update().filter_by(
            id=cart_item.product_variant_id
        ).first()

        if not variant or not variant.is_available:
            return jsonify({
                "error": f"Product is no longer available",
                "item_id": str(cart_item.product_variant_id),
            }), 409

        if variant.stock_qty < cart_item.quantity:
            return jsonify({
                "error": f"Insufficient stock for {variant.product.name}",
                "available": variant.stock_qty,
            }), 409

        price = variant.effective_price
        total += price * cart_item.quantity

        snapshot = {
            "product_id": str(variant.product_id),
            "product_name": variant.product.name,
            "variant_id": str(variant.id),
            "variant_name": variant.name,
            "price_at_purchase": price,
        }

        order_items.append({
            "variant": variant,
            "quantity": cart_item.quantity,
            "price": price,
            "snapshot": snapshot,
        })

    # Create order
    fulfillment_type = data["fulfillment_type"]
    order = Order(
        order_number=_generate_order_number(),
        status="pending",
        fulfillment_type=fulfillment_type,
        total_amount=total,
        billing_address=data["billing_address"],
        shipping_address=data.get("shipping_address") if fulfillment_type == "shipping" else None,
        collection_address=data.get("collection_address") if fulfillment_type == "collection" else None,
        notes=data.get("notes"),
    )
    db.session.add(order)
    db.session.flush()  # get order.id before creating items

    for oi in order_items:
        item = OrderItem(
            order_id=order.id,
            product_variant_id=oi["variant"].id,
            quantity=oi["quantity"],
            price_at_purchase=oi["price"],
            product_snapshot=oi["snapshot"],
        )
        db.session.add(item)

        # Decrement stock
        oi["variant"].stock_qty -= oi["quantity"]
        if oi["variant"].stock_qty <= 0:
            oi["variant"].is_available = False

    db.session.commit()

    # Fire new-order email notification (non-blocking)
    try:
        from app.utils.email import send_order_notification
        send_order_notification(order)
    except Exception as e:
        current_app.logger.error(f"Email notification failed for order {order.order_number}: {e}")

    return jsonify({
        "order_id": str(order.id),
        "order_number": order.order_number,
        "total_amount": float(order.total_amount),
        "status": order.status,
    }), 201


@orders_bp.get("/orders/<string:order_id>")
@limiter.limit("30 per minute")
def get_order(order_id: str):
    """
    GET /api/orders/:id — public order status (confirmation page).
    Returns safe subset — no admin data.
    """
    order = Order.query.filter_by(id=order_id).first()
    if not order:
        return jsonify({"error": "Order not found"}), 404

    return jsonify(order.to_dict(admin=False))



      payments.py


      from datetime import datetime, timezone
from flask import Blueprint, request, jsonify, current_app
from app.extensions import db, limiter
from app.models import Order, Payment
from app.utils.security import generate_payfast_signature, verify_payfast_itn

payments_bp = Blueprint("payments", __name__)

PAYFAST_LIVE_URL = "https://www.payfast.co.za/eng/process"
PAYFAST_SANDBOX_URL = "https://sandbox.payfast.co.za/eng/process"

# IPs PayFast sends ITN from — validate to reject spoofed webhooks
PAYFAST_VALID_IPS = {
    "197.97.145.144", "41.74.179.194", "196.33.227.144",
    "196.33.227.145", "196.33.227.146", "196.33.227.147",
}


# ─── PayFast ─────────────────────────────────────────────────────────────────

@payments_bp.post("/payfast/initiate")
@limiter.limit("5 per minute")
def payfast_initiate():
    """
    POST /api/payments/payfast/initiate
    Body: { order_id }
    Returns: { action_url, form_data } — frontend renders a hidden form and auto-submits.
    """
    data = request.get_json(silent=True) or {}
    order_id = data.get("order_id")
    if not order_id:
        return jsonify({"error": "order_id is required"}), 400

    order = Order.query.filter_by(id=order_id).first()
    if not order:
        return jsonify({"error": "Order not found"}), 404
    if order.status not in ("pending", "confirmed"):
        return jsonify({"error": "Order is not payable"}), 409

    cfg = current_app.config
    merchant_id = cfg["PAYFAST_MERCHANT_ID"]
    merchant_key = cfg["PAYFAST_MERCHANT_KEY"]
    passphrase = cfg["PAYFAST_PASSPHRASE"] or None
    sandbox = cfg["PAYFAST_SANDBOX"]

    # Build return/cancel/notify URLs — update to your actual domain
    base_url = "https://midcenturist.co.za"
    api_url = "https://api.midcenturist.co.za"

    billing = order.billing_address or {}
    name_parts = billing.get("name", "Customer").split(" ", 1)
    first_name = name_parts[0]
    last_name = name_parts[1] if len(name_parts) > 1 else ""

    form_data = {
        "merchant_id": merchant_id,
        "merchant_key": merchant_key,
        "return_url": f"{base_url}/order/{str(order.id)}?payment=success",
        "cancel_url": f"{base_url}/checkout?payment=cancelled",
        "notify_url": f"{api_url}/api/payments/payfast/webhook",
        "name_first": first_name,
        "name_last": last_name,
        "email_address": billing.get("email", ""),
        "m_payment_id": str(order.id),
        "amount": f"{float(order.total_amount):.2f}",
        "item_name": f"Midcenturist SA Order {order.order_number}",
    }

    form_data["signature"] = generate_payfast_signature(form_data.copy(), passphrase)

    action_url = PAYFAST_SANDBOX_URL if sandbox else PAYFAST_LIVE_URL

    # Record payment initiation
    payment = Payment(
        order_id=order.id,
        method="payfast",
        status="initiated",
        amount=order.total_amount,
    )
    db.session.add(payment)
    db.session.commit()

    return jsonify({"action_url": action_url, "form_data": form_data})


@payments_bp.post("/payfast/webhook")
def payfast_webhook():
    """
    POST /api/payments/payfast/webhook — PayFast ITN
    PayFast sends form-encoded POST data. Validate signature + IP, then update order.
    """
    # IP check (skip in sandbox)
    if not current_app.config["PAYFAST_SANDBOX"]:
        client_ip = request.headers.get("X-Forwarded-For", request.remote_addr).split(",")[0].strip()
        if client_ip not in PAYFAST_VALID_IPS:
            current_app.logger.warning(f"PayFast ITN from unknown IP: {client_ip}")
            return "INVALID IP", 403

    post_data = request.form.to_dict()
    passphrase = current_app.config["PAYFAST_PASSPHRASE"] or None

    if not verify_payfast_itn(post_data, passphrase):
        current_app.logger.warning("PayFast ITN signature verification failed")
        return "INVALID SIGNATURE", 400

    payment_status = post_data.get("payment_status")
    order_id = post_data.get("m_payment_id")
    pf_payment_id = post_data.get("pf_payment_id")

    order = Order.query.filter_by(id=order_id).first()
    if not order:
        return "ORDER NOT FOUND", 404

    payment = Payment.query.filter_by(order_id=order_id, method="payfast").order_by(
        Payment.id.desc()
    ).first()

    if payment_status == "COMPLETE":
        if payment:
            payment.status = "completed"
            payment.transaction_id = pf_payment_id
            payment.paid_at = datetime.now(timezone.utc)
            payment.raw_webhook = post_data
        order.status = "paid"
        db.session.commit()

        # Fire confirmation emails
        try:
            from app.utils.email import send_order_confirmation, send_new_order_alert
            send_order_confirmation(order)
            send_new_order_alert(order)
        except Exception as e:
            current_app.logger.error(f"Email failed after PayFast payment: {e}")

    elif payment_status in ("FAILED", "CANCELLED"):
        if payment:
            payment.status = "failed" if payment_status == "FAILED" else "cancelled"
            payment.raw_webhook = post_data
        db.session.commit()

    return "OK", 200


# ─── Yoco ────────────────────────────────────────────────────────────────────

@payments_bp.post("/yoco/initiate")
@limiter.limit("5 per minute")
def yoco_initiate():
    """
    POST /api/payments/yoco/initiate
    Body: { order_id, token }  — token comes from Yoco popup on the frontend
    """
    data = request.get_json(silent=True) or {}
    order_id = data.get("order_id")
    token = data.get("token")

    if not order_id or not token:
        return jsonify({"error": "order_id and token are required"}), 400

    order = Order.query.filter_by(id=order_id).first()
    if not order:
        return jsonify({"error": "Order not found"}), 404

    import requests as req
    yoco_secret = current_app.config["YOCO_SECRET_KEY"]

    response = req.post(
        "https://online.yoco.com/v1/charges/",
        json={
            "token": token,
            "amountInCents": int(float(order.total_amount) * 100),
            "currency": "ZAR",
        },
        headers={"X-Auth-Secret-Key": yoco_secret},
        timeout=30,
    )

    result = response.json()
    payment = Payment(
        order_id=order.id,
        method="yoco",
        status="initiated",
        amount=order.total_amount,
    )
    db.session.add(payment)

    if response.status_code == 201 and result.get("status") == "successful":
        payment.status = "completed"
        payment.transaction_id = result.get("id")
        payment.paid_at = datetime.now(timezone.utc)
        payment.raw_webhook = result
        order.status = "paid"
        db.session.commit()

        try:
            from app.utils.email import send_order_confirmation, send_new_order_alert
            send_order_confirmation(order)
            send_new_order_alert(order)
        except Exception as e:
            current_app.logger.error(f"Email failed after Yoco payment: {e}")

        return jsonify({"status": "paid", "order_number": order.order_number}), 200

    else:
        payment.status = "failed"
        payment.raw_webhook = result
        db.session.commit()
        return jsonify({"error": "Payment failed", "detail": result.get("message")}), 402




        newsletter.py


        from flask import Blueprint, request, jsonify
from app.extensions import db, limiter
from app.models import Subscriber, Review, Product
from app.utils.validators import is_valid_email, validate_review, sanitise_string
from sqlalchemy.exc import IntegrityError

newsletter_bp = Blueprint("newsletter", __name__)
reviews_bp = Blueprint("reviews", __name__)


@newsletter_bp.post("/newsletter/subscribe")
@limiter.limit("3 per minute")
def subscribe():
    """POST /api/newsletter/subscribe"""
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()

    if not is_valid_email(email):
        return jsonify({"error": "Invalid email address"}), 422

    existing = Subscriber.query.filter_by(email=email).first()
    if existing:
        if not existing.is_active:
            existing.is_active = True
            db.session.commit()
            return jsonify({"message": "Welcome back! You've been re-subscribed."}), 200
        return jsonify({"message": "Already subscribed"}), 200

    sub = Subscriber(
        email=email,
        first_name=sanitise_string(data.get("first_name"), 100),
        last_name=sanitise_string(data.get("last_name"), 100),
        phone=sanitise_string(data.get("phone"), 30),
        area=sanitise_string(data.get("area"), 100),
        source=sanitise_string(data.get("source"), 50) or "footer",
    )
    db.session.add(sub)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify({"message": "Already subscribed"}), 200

    return jsonify({"message": "Subscribed successfully"}), 201


@reviews_bp.post("/reviews")
@limiter.limit("3 per minute")
def submit_review():
    """POST /api/reviews"""
    data = request.get_json(silent=True) or {}

    product_id = data.get("product_id")
    product = Product.query.filter_by(id=product_id).first() if product_id else None
    if not product:
        return jsonify({"error": "Product not found"}), 404

    errors = validate_review(data)
    if errors:
        return jsonify({"errors": errors}), 422

    review = Review(
        product_id=product.id,
        reviewer_name=sanitise_string(data.get("reviewer_name"), 100),
        rating=int(data["rating"]),
        comment=sanitise_string(data.get("comment"), 2000),
        is_approved=False,
    )
    db.session.add(review)
    db.session.commit()

    return jsonify({"message": "Review submitted — it will appear once approved"}), 201




    products.py

    import re
from datetime import datetime, timezone, timedelta
from flask import Blueprint, request, jsonify, current_app
from app.extensions import db, limiter
from app.models import Product, ProductVariant, ProductImage, Category
from app.utils.security import require_admin
from app.utils.validators import validate_product, sanitise_string

admin_products_bp = Blueprint("admin_products", __name__)


def slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_-]+", "-", text)
    text = re.sub(r"^-+|-+$", "", text)
    return text


def unique_slug(name: str) -> str:
    base = slugify(name)
    slug = base
    counter = 1
    while Product.query.filter_by(slug=slug).first():
        slug = f"{base}-{counter}"
        counter += 1
    return slug


@admin_products_bp.get("/products")
@require_admin
def admin_list_products():
    """GET /api/admin/products — all products, all statuses."""
    q = Product.query

    status = request.args.get("status")
    if status:
        q = q.filter(Product.status == status)

    category_slug = request.args.get("category")
    if category_slug:
        cat = Category.query.filter_by(slug=category_slug).first()
        if cat:
            q = q.filter(Product.category_id == cat.id)

    search = request.args.get("search")
    if search:
        q = q.filter(Product.name.ilike(f"%{search}%"))

    sort = request.args.get("sort", "newest")
    if sort == "newest":
        q = q.order_by(Product.created_at.desc())
    elif sort == "price-high":
        q = q.join(ProductVariant).order_by(ProductVariant.price.desc())
    elif sort == "price-low":
        q = q.join(ProductVariant).order_by(ProductVariant.price.asc())
    elif sort == "name":
        q = q.order_by(Product.name.asc())

    page = max(1, int(request.args.get("page", 1)))
    limit = min(50, int(request.args.get("limit", 20)))
    total = q.count()
    products = q.offset((page - 1) * limit).limit(limit).all()

    return jsonify({
        "products": [p.to_dict() for p in products],
        "total": total,
        "page": page,
        "limit": limit,
    })


@admin_products_bp.post("/products")
@require_admin
def admin_create_product():
    """POST /api/admin/products"""
    data = request.get_json(silent=True) or {}
    errors = validate_product(data)
    if errors:
        return jsonify({"errors": errors}), 422

    category_id = None
    if data.get("category_id"):
        cat = Category.query.filter_by(id=data["category_id"]).first()
        if cat:
            category_id = cat.id

    product = Product(
        name=sanitise_string(data["name"], 255),
        slug=unique_slug(data["name"]),
        description=sanitise_string(data.get("description"), 10000),
        category_id=category_id,
        era=sanitise_string(data.get("era"), 100),
        material=sanitise_string(data.get("material"), 255),
        year=data.get("year"),
        condition=data.get("condition"),
        status=data.get("status", "draft"),
        badge=data.get("badge"),
        is_featured=bool(data.get("is_featured", False)),
        is_unique=bool(data.get("is_unique", False)),
        instagram_post_id=sanitise_string(data.get("instagram_post_id"), 255),
        instagram_post_url=sanitise_string(data.get("instagram_post_url"), 500),
    )
    db.session.add(product)
    db.session.flush()

    # Create variants
    variants = data.get("variants", [])
    if not variants and data.get("price") is not None:
        # Single-price product — create a default variant
        variants = [{"price": data["price"], "sale_price": data.get("sale_price")}]

    for v_data in variants:
        variant = ProductVariant(
            product_id=product.id,
            name=sanitise_string(v_data.get("name"), 255),
            price=float(v_data.get("price", 0)),
            sale_price=float(v_data["sale_price"]) if v_data.get("sale_price") else None,
            sku=sanitise_string(v_data.get("sku"), 100),
            stock_qty=int(v_data.get("stock_qty", 1)),
        )
        db.session.add(variant)

    db.session.commit()
    return jsonify(product.to_dict()), 201


@admin_products_bp.put("/products/<string:product_id>")
@require_admin
def admin_update_product(product_id: str):
    """PUT /api/admin/products/:id"""
    product = Product.query.filter_by(id=product_id).first()
    if not product:
        return jsonify({"error": "Product not found"}), 404

    data = request.get_json(silent=True) or {}
    errors = validate_product(data, is_update=True)
    if errors:
        return jsonify({"errors": errors}), 422

    # Updatable fields
    updatable = [
        "name", "description", "era", "material", "year", "condition",
        "badge", "is_featured", "is_unique", "instagram_post_id",
        "instagram_post_url", "status",
    ]
    for field in updatable:
        if field in data:
            setattr(product, field, data[field])

    if "category_id" in data:
        cat = Category.query.filter_by(id=data["category_id"]).first()
        product.category_id = cat.id if cat else None

    # Handle sold status automatically
    if data.get("status") == "sold" and not product.sold_at:
        product.sold_at = datetime.now(timezone.utc)
        product.archive_at = product.sold_at + timedelta(days=30)

    db.session.commit()
    return jsonify(product.to_dict())


@admin_products_bp.post("/products/<string:product_id>/mark-sold")
@require_admin
def admin_mark_sold(product_id: str):
    """POST /api/admin/products/:id/mark-sold"""
    product = Product.query.filter_by(id=product_id).first()
    if not product:
        return jsonify({"error": "Product not found"}), 404

    product.status = "sold"
    product.sold_at = datetime.now(timezone.utc)
    product.archive_at = product.sold_at + timedelta(days=30)

    # Mark all variants unavailable
    for variant in product.variants:
        variant.is_available = False

    db.session.commit()
    return jsonify(product.to_dict())


@admin_products_bp.delete("/products/<string:product_id>")
@require_admin
def admin_delete_product(product_id: str):
    """DELETE /api/admin/products/:id — soft delete by default."""
    product = Product.query.filter_by(id=product_id).first()
    if not product:
        return jsonify({"error": "Product not found"}), 404

    permanent = request.args.get("permanent") == "true"
    if permanent:
        db.session.delete(product)
    else:
        product.status = "archived"

    db.session.commit()
    return jsonify({"message": "Product deleted" if permanent else "Product archived"})


@admin_products_bp.post("/products/<string:product_id>/images")
@require_admin
def admin_upload_image(product_id: str):
    """POST /api/admin/products/:id/images — upload to Cloudinary, save URL."""
    product = Product.query.filter_by(id=product_id).first()
    if not product:
        return jsonify({"error": "Product not found"}), 404

    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400

    file = request.files["file"]

    try:
        import cloudinary.uploader
        result = cloudinary.uploader.upload(
            file,
            folder=f"midcenturist/products/{product_id}",
            transformation=[{"quality": "auto", "fetch_format": "auto"}],
        )
        url = result["secure_url"]
    except Exception as e:
        current_app.logger.error(f"Cloudinary upload failed: {e}")
        return jsonify({"error": "Image upload failed"}), 500

    # First image is primary by default
    is_primary = len(product.images) == 0
    sort_order = len(product.images)

    image = ProductImage(
        product_id=product.id,
        url=url,
        alt_text=sanitise_string(request.form.get("alt_text"), 255),
        sort_order=sort_order,
        is_primary=is_primary,
    )
    db.session.add(image)
    db.session.commit()

    return jsonify(image.to_dict()), 201


@admin_products_bp.delete("/products/<string:product_id>/images/<string:image_id>")
@require_admin
def admin_delete_image(product_id: str, image_id: str):
    """DELETE /api/admin/products/:id/images/:imgId"""
    image = ProductImage.query.filter_by(id=image_id, product_id=product_id).first()
    if not image:
        return jsonify({"error": "Image not found"}), 404

    # Delete from Cloudinary if URL is a Cloudinary URL
    try:
        if "cloudinary.com" in image.url:
            import cloudinary.uploader
            public_id = image.url.split("/upload/")[1].rsplit(".", 1)[0]
            cloudinary.uploader.destroy(public_id)
    except Exception as e:
        current_app.logger.warning(f"Cloudinary delete failed: {e}")

    db.session.delete(image)
    db.session.commit()

    # If we deleted the primary, promote the next image
    product = Product.query.filter_by(id=product_id).first()
    if product and product.images and not any(i.is_primary for i in product.images):
        product.images[0].is_primary = True
        db.session.commit()

    return jsonify({"message": "Image deleted"})




    __init__.py

from flask import Blueprint, request, jsonify, current_app
from app.extensions import db, limiter
from app.models import Order, Category, Review, Product
from app.utils.security import require_admin
from app.utils.validators import sanitise_string, VALID_ORDER_STATUSES
import re

admin_orders_bp = Blueprint("admin_orders", __name__)
admin_categories_bp = Blueprint("admin_categories", __name__)
admin_instagram_bp = Blueprint("admin_instagram", __name__)
admin_reviews_bp = Blueprint("admin_reviews", __name__)


# ─── Admin Orders ─────────────────────────────────────────────────────────────

@admin_orders_bp.get("/orders")
@require_admin
def admin_list_orders():
    q = Order.query

    status = request.args.get("status")
    if status:
        q = q.filter(Order.status == status)

    fulfillment = request.args.get("fulfillment_type")
    if fulfillment:
        q = q.filter(Order.fulfillment_type == fulfillment)

    page = max(1, int(request.args.get("page", 1)))
    limit = min(50, int(request.args.get("limit", 20)))
    total = q.count()
    orders = q.order_by(Order.created_at.desc()).offset((page - 1) * limit).limit(limit).all()

    return jsonify({
        "orders": [o.to_dict(admin=True) for o in orders],
        "total": total,
        "page": page,
    })


@admin_orders_bp.get("/orders/<string:order_id>")
@require_admin
def admin_get_order(order_id: str):
    order = Order.query.filter_by(id=order_id).first()
    if not order:
        return jsonify({"error": "Order not found"}), 404
    return jsonify(order.to_dict(admin=True))


@admin_orders_bp.put("/orders/<string:order_id>/status")
@require_admin
def admin_update_order_status(order_id: str):
    order = Order.query.filter_by(id=order_id).first()
    if not order:
        return jsonify({"error": "Order not found"}), 404

    data = request.get_json(silent=True) or {}
    new_status = data.get("status")
    if new_status not in VALID_ORDER_STATUSES:
        return jsonify({"error": f"Invalid status. Valid: {', '.join(VALID_ORDER_STATUSES)}"}), 422

    old_status = order.status
    order.status = new_status
    db.session.commit()

    # Send status update email to customer
    if new_status != old_status:
        try:
            from app.utils.email import send_status_update
            send_status_update(order)
        except Exception as e:
            current_app.logger.error(f"Status email failed: {e}")

    return jsonify(order.to_dict(admin=True))


# ─── Admin Categories ─────────────────────────────────────────────────────────

def _slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    return re.sub(r"[\s_-]+", "-", text).strip("-")


@admin_categories_bp.post("/categories")
@require_admin
def admin_create_category():
    data = request.get_json(silent=True) or {}
    name = data.get("name", "").strip()
    if not name:
        return jsonify({"error": "name is required"}), 422

    slug = _slugify(name)
    if Category.query.filter_by(slug=slug).first():
        return jsonify({"error": "A category with this name already exists"}), 409

    cat = Category(
        name=name,
        slug=slug,
        parent_id=data.get("parent_id"),
    )
    db.session.add(cat)
    db.session.commit()
    return jsonify(cat.to_dict()), 201


@admin_categories_bp.put("/categories/<string:category_id>")
@require_admin
def admin_update_category(category_id: str):
    cat = Category.query.filter_by(id=category_id).first()
    if not cat:
        return jsonify({"error": "Category not found"}), 404

    data = request.get_json(silent=True) or {}
    if "name" in data:
        cat.name = data["name"].strip()
        cat.slug = _slugify(cat.name)
    if "parent_id" in data:
        cat.parent_id = data["parent_id"]

    db.session.commit()
    return jsonify(cat.to_dict())


# ─── Admin Instagram Sync ─────────────────────────────────────────────────────

@admin_instagram_bp.post("/instagram/sync")
@require_admin
@limiter.limit("5 per hour")
def admin_instagram_sync():
    """
    POST /api/admin/instagram/sync
    Pulls latest posts from Meta Graph API.
    Creates draft products for any post not already in the DB.
    Returns count of new drafts created.
    """
    cfg = current_app.config
    token = cfg.get("INSTAGRAM_ACCESS_TOKEN")
    account_id = cfg.get("INSTAGRAM_BUSINESS_ACCOUNT_ID")

    if not token or not account_id:
        return jsonify({"error": "Instagram not configured — add INSTAGRAM_ACCESS_TOKEN and INSTAGRAM_BUSINESS_ACCOUNT_ID to env"}), 503

    import requests as req
    url = f"https://graph.instagram.com/{account_id}/media"
    params = {
        "fields": "id,caption,media_url,permalink,timestamp,media_type",
        "access_token": token,
        "limit": 20,
    }

    try:
        response = req.get(url, params=params, timeout=10)
        response.raise_for_status()
        media_data = response.json().get("data", [])
    except Exception as e:
        current_app.logger.error(f"Instagram API error: {e}")
        return jsonify({"error": "Failed to fetch Instagram posts"}), 502

    new_drafts = []
    for post in media_data:
        if post.get("media_type") not in ("IMAGE", "CAROUSEL_ALBUM"):
            continue

        post_id = post["id"]
        # Skip if already imported
        if Product.query.filter_by(instagram_post_id=post_id).first():
            continue

        # Parse caption into product name + description
        caption = post.get("caption", "")
        lines = caption.strip().split("\n")
        name = lines[0][:255] if lines else f"Instagram Post {post_id}"
        description = "\n".join(lines[1:]).strip() if len(lines) > 1 else ""

        product = Product(
            name=sanitise_string(name, 255),
            slug=_unique_slug_from_name(name),
            description=sanitise_string(description, 10000),
            status="draft",
            instagram_post_id=post_id,
            instagram_post_url=post.get("permalink", ""),
        )
        db.session.add(product)
        db.session.flush()

        # Save IG image URL
        if post.get("media_url"):
            image = ProductImage(
                product_id=product.id,
                url=post["media_url"],
                is_primary=True,
                sort_order=0,
            )
            db.session.add(image)

        new_drafts.append({"post_id": post_id, "name": name})

    db.session.commit()

    return jsonify({
        "synced": len(new_drafts),
        "new_drafts": new_drafts,
        "message": f"{len(new_drafts)} new draft(s) created" if new_drafts else "No new posts found",
    })


@admin_instagram_bp.get("/instagram/posts")
@require_admin
def admin_instagram_posts():
    """GET /api/admin/instagram/posts — preview raw posts before import."""
    cfg = current_app.config
    token = cfg.get("INSTAGRAM_ACCESS_TOKEN")
    account_id = cfg.get("INSTAGRAM_BUSINESS_ACCOUNT_ID")

    if not token or not account_id:
        return jsonify({"error": "Instagram not configured"}), 503

    import requests as req
    params = {
        "fields": "id,caption,media_url,permalink,timestamp",
        "access_token": token,
        "limit": 20,
    }
    try:
        response = req.get(
            f"https://graph.instagram.com/{account_id}/media",
            params=params, timeout=10
        )
        response.raise_for_status()
        posts = response.json().get("data", [])
    except Exception as e:
        return jsonify({"error": str(e)}), 502

    # Mark which ones are already imported
    for post in posts:
        existing = Product.query.filter_by(instagram_post_id=post["id"]).first()
        post["already_imported"] = existing is not None

    return jsonify({"posts": posts})


def _unique_slug_from_name(name: str) -> str:
    import re as _re
    base = _re.sub(r"[\s_-]+", "-", _re.sub(r"[^\w\s-]", "", name.lower().strip())).strip("-")
    slug = base
    counter = 1
    while Product.query.filter_by(slug=slug).first():
        slug = f"{base}-{counter}"
        counter += 1
    return slug


# ─── Admin Reviews ────────────────────────────────────────────────────────────

@admin_reviews_bp.get("/reviews")
@require_admin
def admin_list_reviews():
    """GET /api/admin/reviews?approved=false"""
    approved_param = request.args.get("approved")
    q = Review.query

    if approved_param == "false":
        q = q.filter(Review.is_approved == False)
    elif approved_param == "true":
        q = q.filter(Review.is_approved == True)

    reviews = q.order_by(Review.created_at.desc()).all()
    return jsonify({"reviews": [r.to_dict() for r in reviews]})


@admin_reviews_bp.put("/reviews/<string:review_id>/approve")
@require_admin
def admin_approve_review(review_id: str):
    review = Review.query.filter_by(id=review_id).first()
    if not review:
        return jsonify({"error": "Review not found"}), 404

    data = request.get_json(silent=True) or {}
    review.is_approved = bool(data.get("approved", True))
    db.session.commit()

    action = "approved" if review.is_approved else "rejected"
    return jsonify({"message": f"Review {action}", "review": review.to_dict()})