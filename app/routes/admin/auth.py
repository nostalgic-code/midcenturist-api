import hmac
from flask import Blueprint, request, jsonify, current_app
from app.extensions import limiter
from app.utils.security import generate_admin_token

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
