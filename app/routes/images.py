from flask import Blueprint, Response
from app.extensions import limiter
from app.models import ProductImage

images_bp = Blueprint("images", __name__)


@images_bp.get("/images/<string:image_id>")
@limiter.limit("120 per minute")
def serve_image(image_id: str):
    """GET /api/images/:id — serve image binary from PostgreSQL."""
    image = ProductImage.query.filter_by(id=image_id).first()
    if not image or image.data is None:
        return Response("Not found", status=404)

    return Response(
        image.data,
        mimetype=image.content_type or "application/octet-stream",
        headers={
            "Cache-Control": "public, max-age=31536000, immutable",
        },
    )
