import hmac
import jwt
from flask import Blueprint, request, jsonify, current_app
from app.extensions import db, limiter
from app.models import Product, Order, Category, Collection
from app.utils.security import generate_admin_token, require_admin

admin_auth_bp = Blueprint("admin_auth", __name__)


@admin_auth_bp.post("/login")
@limiter.limit("5 per minute")
def admin_login():
    """
    POST /api/admin/login
    Body: { "email": "...", "password": "..." }
    Returns: { "token": "jwt..." }
    """
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    if not email or not password:
        return jsonify({"error": "Email and password are required"}), 400

    expected_email = current_app.config.get("ADMIN_EMAIL", "").strip().lower()
    expected_password = current_app.config.get("ADMIN_PASSWORD", "")

    if not expected_email or not expected_password:
        return jsonify({"error": "Admin credentials not configured"}), 500

    # Constant-time comparison to prevent timing attacks
    email_match = hmac.compare_digest(email, expected_email)
    password_match = hmac.compare_digest(password, expected_password)

    if not email_match or not password_match:
        return jsonify({"error": "Invalid email or password"}), 401

    token = generate_admin_token(email)
    return jsonify({"token": token})


@admin_auth_bp.get("/dashboard")
@require_admin
def admin_dashboard():
    """
    GET /api/admin/dashboard
    Returns admin profile + store stats.
    """
    # Extract admin email from token
    auth = request.headers.get("Authorization", "")
    token = auth.split(" ", 1)[1] if auth.startswith("Bearer ") else ""
    try:
        payload = jwt.decode(
            token,
            current_app.config["ADMIN_JWT_SECRET"],
            algorithms=["HS256"],
        )
        admin_email = payload.get("sub", "")
    except jwt.InvalidTokenError:
        admin_email = ""

    # Gather store stats
    total_products = Product.query.count()
    live_products = Product.query.filter_by(status="live").count()
    draft_products = Product.query.filter_by(status="draft").count()
    sold_products = Product.query.filter_by(status="sold").count()

    total_orders = Order.query.count()
    pending_orders = Order.query.filter_by(status="pending").count()
    confirmed_orders = Order.query.filter_by(status="confirmed").count()
    paid_orders = Order.query.filter_by(status="paid").count()

    total_categories = Category.query.count()
    total_collections = Collection.query.count()

    # Revenue from paid/shipped/delivered orders
    revenue_statuses = {"paid", "shipped", "collected", "delivered"}
    revenue_orders = Order.query.filter(Order.status.in_(revenue_statuses)).all()
    total_revenue = sum(float(o.total_amount) for o in revenue_orders)

    return jsonify({
        "admin": {
            "email": admin_email,
            "role": "admin",
        },
        "stats": {
            "products": {
                "total": total_products,
                "live": live_products,
                "draft": draft_products,
                "sold": sold_products,
            },
            "orders": {
                "total": total_orders,
                "pending": pending_orders,
                "confirmed": confirmed_orders,
                "paid": paid_orders,
            },
            "categories": total_categories,
            "collections": total_collections,
            "revenue": total_revenue,
        },
    })
