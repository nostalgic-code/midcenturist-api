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
