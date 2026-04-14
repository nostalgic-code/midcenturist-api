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
