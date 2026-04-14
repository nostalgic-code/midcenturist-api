import hmac
import jwt
from datetime import datetime, timezone
from flask import Blueprint, request, jsonify, current_app
from app.extensions import db, limiter
from app.models import Product, Order, Category, Collection, Subscriber, Review
from app.utils.security import generate_admin_token, require_admin

admin_auth_bp = Blueprint("admin_auth", __name__)


@admin_auth_bp.post("/login")
@limiter.limit("5 per minute")
def admin_login():
    """
    POST /api/admin/login
    Body: { "email": "...", "password": "..." }
    Returns: { "token": "jwt...", "expires_in": 86400 }
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
    return jsonify({"token": token, "expires_in": 86400})


@admin_auth_bp.get("/dashboard")
@require_admin
def admin_dashboard():
    """
    GET /api/admin/dashboard
    Returns flat stats object matching CMS DashboardStats interface.
    """
    live_products = Product.query.filter_by(status="live").count()
    draft_products = Product.query.filter_by(status="draft").count()
    sold_products = Product.query.filter_by(status="sold").count()

    # Orders created this month
    now = datetime.now(timezone.utc)
    first_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    orders_this_month = Order.query.filter(Order.created_at >= first_of_month).count()
    pending_orders = Order.query.filter_by(status="pending").count()

    total_subscribers = Subscriber.query.filter_by(is_active=True).count()
    pending_reviews = Review.query.filter_by(is_approved=False).count()

    # Drafts created from Instagram
    drafts_from_instagram = Product.query.filter(
        Product.status == "draft",
        Product.instagram_post_id.isnot(None),
    ).count()

    return jsonify({
        "live_products": live_products,
        "draft_products": draft_products,
        "sold_products": sold_products,
        "orders_this_month": orders_this_month,
        "pending_orders": pending_orders,
        "total_subscribers": total_subscribers,
        "pending_reviews": pending_reviews,
        "drafts_from_instagram": drafts_from_instagram,
    })
