import re
from flask import Blueprint, request, jsonify
from app.extensions import db
from app.models import UpcomingItem, Product, ProductVariant
from app.utils.security import require_admin
from app.utils.validators import sanitise_string

admin_upcoming_bp = Blueprint("admin_upcoming", __name__)

VALID_UPCOMING_STATUSES = {"coming-soon", "sourced", "in-restoration", "expected-this-week"}


def _slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    return re.sub(r"[\s_-]+", "-", text).strip("-")


def _unique_slug(name: str) -> str:
    base = _slugify(name)
    slug = base
    counter = 1
    while Product.query.filter_by(slug=slug).first():
        slug = f"{base}-{counter}"
        counter += 1
    return slug


@admin_upcoming_bp.get("/upcoming")
@require_admin
def admin_list_upcoming():
    """
    GET /api/admin/upcoming
    Query params: status, page, limit
    """
    q = UpcomingItem.query

    status = request.args.get("status")
    if status and status in VALID_UPCOMING_STATUSES:
        q = q.filter(UpcomingItem.status == status)

    page = max(1, int(request.args.get("page", 1)))
    limit = min(50, int(request.args.get("limit", 20)))
    total = q.count()
    items = (
        q.order_by(UpcomingItem.sort_order.asc(), UpcomingItem.created_at.desc())
        .offset((page - 1) * limit)
        .limit(limit)
        .all()
    )

    return jsonify({
        "upcoming": [i.to_dict() for i in items],
        "total": total,
        "page": page,
        "limit": limit,
    })


@admin_upcoming_bp.post("/upcoming")
@require_admin
def admin_create_upcoming():
    """POST /api/admin/upcoming"""
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    if not name:
        return jsonify({"error": "name is required"}), 422

    status = data.get("status", "coming-soon")
    if status not in VALID_UPCOMING_STATUSES:
        return jsonify({"error": f"Invalid status. Valid: {', '.join(VALID_UPCOMING_STATUSES)}"}), 422

    item = UpcomingItem(
        name=sanitise_string(name, 255),
        description=sanitise_string(data.get("description"), 10000),
        estimated_price=float(data["estimated_price"]) if data.get("estimated_price") else None,
        status=status,
        sort_order=int(data.get("sort_order", 0)),
    )
    db.session.add(item)
    db.session.commit()
    return jsonify(item.to_dict()), 201


@admin_upcoming_bp.put("/upcoming/<string:item_id>")
@require_admin
def admin_update_upcoming(item_id: str):
    """PUT /api/admin/upcoming/:id"""
    item = UpcomingItem.query.filter_by(id=item_id).first()
    if not item:
        return jsonify({"error": "Upcoming item not found"}), 404

    data = request.get_json(silent=True) or {}

    if "name" in data:
        item.name = sanitise_string(data["name"], 255)
    if "description" in data:
        item.description = sanitise_string(data["description"], 10000)
    if "estimated_price" in data:
        item.estimated_price = float(data["estimated_price"]) if data["estimated_price"] else None
    if "status" in data:
        if data["status"] not in VALID_UPCOMING_STATUSES:
            return jsonify({"error": f"Invalid status. Valid: {', '.join(VALID_UPCOMING_STATUSES)}"}), 422
        item.status = data["status"]
    if "sort_order" in data:
        item.sort_order = int(data["sort_order"])

    db.session.commit()
    return jsonify(item.to_dict())


@admin_upcoming_bp.delete("/upcoming/<string:item_id>")
@require_admin
def admin_delete_upcoming(item_id: str):
    """DELETE /api/admin/upcoming/:id"""
    item = UpcomingItem.query.filter_by(id=item_id).first()
    if not item:
        return jsonify({"error": "Upcoming item not found"}), 404

    db.session.delete(item)
    db.session.commit()
    return jsonify({"message": "Upcoming item deleted"})


@admin_upcoming_bp.post("/upcoming/<string:item_id>/convert")
@require_admin
def admin_convert_upcoming(item_id: str):
    """
    POST /api/admin/upcoming/:id/convert
    Converts an upcoming item into a draft product,
    then deletes the upcoming item.
    Returns the new product.
    """
    item = UpcomingItem.query.filter_by(id=item_id).first()
    if not item:
        return jsonify({"error": "Upcoming item not found"}), 404

    product = Product(
        name=item.name,
        slug=_unique_slug(item.name),
        description=item.description,
        status="draft",
    )
    db.session.add(product)
    db.session.flush()

    # Create a default variant if estimated_price exists
    if item.estimated_price:
        variant = ProductVariant(
            product_id=product.id,
            price=item.estimated_price,
            stock_qty=1,
        )
        db.session.add(variant)

    db.session.delete(item)
    db.session.commit()

    return jsonify(product.to_dict()), 201
