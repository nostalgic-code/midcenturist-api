from flask import Blueprint, request, jsonify
from app.extensions import db
from app.models import Subscriber
from app.utils.security import require_admin

admin_subscribers_bp = Blueprint("admin_subscribers", __name__)


@admin_subscribers_bp.get("/subscribers")
@require_admin
def admin_list_subscribers():
    """
    GET /api/admin/subscribers
    Query params: status (active|inactive), search, page, limit
    """
    q = Subscriber.query

    status = request.args.get("status")
    if status == "active":
        q = q.filter(Subscriber.is_active.is_(True))
    elif status == "inactive":
        q = q.filter(Subscriber.is_active.is_(False))

    search = request.args.get("search")
    if search:
        like = f"%{search}%"
        q = q.filter(
            db.or_(
                Subscriber.email.ilike(like),
                Subscriber.first_name.ilike(like),
                Subscriber.last_name.ilike(like),
            )
        )

    page = max(1, int(request.args.get("page", 1)))
    limit = min(50, int(request.args.get("limit", 20)))
    total = q.count()
    subscribers = (
        q.order_by(Subscriber.created_at.desc())
        .offset((page - 1) * limit)
        .limit(limit)
        .all()
    )

    return jsonify({
        "subscribers": [s.to_dict() for s in subscribers],
        "total": total,
        "page": page,
        "limit": limit,
    })


@admin_subscribers_bp.delete("/subscribers/<string:subscriber_id>")
@require_admin
def admin_delete_subscriber(subscriber_id: str):
    """DELETE /api/admin/subscribers/:id"""
    subscriber = Subscriber.query.filter_by(id=subscriber_id).first()
    if not subscriber:
        return jsonify({"error": "Subscriber not found"}), 404

    db.session.delete(subscriber)
    db.session.commit()
    return jsonify({"message": "Subscriber deleted"})
