from flask import Blueprint, request, jsonify, current_app
from app.extensions import db, limiter
from app.models import Order, Category, Review, Product, ProductImage
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
