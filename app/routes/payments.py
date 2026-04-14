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
