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
