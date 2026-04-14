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
