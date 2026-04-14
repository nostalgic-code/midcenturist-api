from flask import Blueprint, request, jsonify
from app.extensions import db
from app.models import Enquiry
from app.utils.security import require_admin

admin_enquiries_bp = Blueprint("admin_enquiries", __name__)

VALID_ENQUIRY_STATUSES = {"unread", "read", "replied"}


@admin_enquiries_bp.get("/enquiries")
@require_admin
def admin_list_enquiries():
    """
    GET /api/admin/enquiries
    Query params: status (unread|read|replied), page, limit
    """
    q = Enquiry.query

    status = request.args.get("status")
    if status and status in VALID_ENQUIRY_STATUSES:
        q = q.filter(Enquiry.status == status)

    page = max(1, int(request.args.get("page", 1)))
    limit = min(50, int(request.args.get("limit", 20)))
    total = q.count()
    enquiries = (
        q.order_by(Enquiry.created_at.desc())
        .offset((page - 1) * limit)
        .limit(limit)
        .all()
    )

    return jsonify({
        "enquiries": [e.to_dict() for e in enquiries],
        "total": total,
        "page": page,
        "limit": limit,
    })


@admin_enquiries_bp.patch("/enquiries/<string:enquiry_id>")
@require_admin
def admin_update_enquiry(enquiry_id: str):
    """
    PATCH /api/admin/enquiries/:id
    Body: { "status": "read" | "replied" }
    """
    enquiry = Enquiry.query.filter_by(id=enquiry_id).first()
    if not enquiry:
        return jsonify({"error": "Enquiry not found"}), 404

    data = request.get_json(silent=True) or {}
    new_status = data.get("status")
    if new_status and new_status in VALID_ENQUIRY_STATUSES:
        enquiry.status = new_status

    db.session.commit()
    return jsonify(enquiry.to_dict())
