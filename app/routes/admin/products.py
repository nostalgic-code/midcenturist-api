import re
from datetime import datetime, timezone, timedelta
from flask import Blueprint, request, jsonify, current_app
from app.extensions import db, limiter
from app.models import Product, ProductVariant, ProductImage, Category
from app.utils.security import require_admin
from app.utils.validators import validate_product, sanitise_string

admin_products_bp = Blueprint("admin_products", __name__)


def slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_-]+", "-", text)
    text = re.sub(r"^-+|-+$", "", text)
    return text


def unique_slug(name: str) -> str:
    base = slugify(name)
    slug = base
    counter = 1
    while Product.query.filter_by(slug=slug).first():
        slug = f"{base}-{counter}"
        counter += 1
    return slug


@admin_products_bp.get("/products")
@require_admin
def admin_list_products():
    """GET /api/admin/products — all products, all statuses."""
    q = Product.query

    status = request.args.get("status")
    if status:
        q = q.filter(Product.status == status)

    category_slug = request.args.get("category")
    if category_slug:
        cat = Category.query.filter_by(slug=category_slug).first()
        if cat:
            q = q.filter(Product.category_id == cat.id)

    search = request.args.get("search")
    if search:
        q = q.filter(Product.name.ilike(f"%{search}%"))

    sort = request.args.get("sort", "newest")
    if sort == "newest":
        q = q.order_by(Product.created_at.desc())
    elif sort == "price-high":
        q = q.join(ProductVariant).order_by(ProductVariant.price.desc())
    elif sort == "price-low":
        q = q.join(ProductVariant).order_by(ProductVariant.price.asc())
    elif sort == "name":
        q = q.order_by(Product.name.asc())

    page = max(1, int(request.args.get("page", 1)))
    limit = min(50, int(request.args.get("limit", 20)))
    total = q.count()
    products = q.offset((page - 1) * limit).limit(limit).all()

    return jsonify({
        "products": [p.to_dict() for p in products],
        "total": total,
        "page": page,
        "limit": limit,
    })


@admin_products_bp.get("/products/<string:product_id>")
@require_admin
def admin_get_product(product_id: str):
    """GET /api/admin/products/:id — single product by UUID."""
    product = Product.query.filter_by(id=product_id).first()
    if not product:
        return jsonify({"error": "Product not found"}), 404
    return jsonify(product.to_dict(include_reviews=True))


@admin_products_bp.post("/products")
@require_admin
def admin_create_product():
    """POST /api/admin/products"""
    data = request.get_json(silent=True) or {}
    errors = validate_product(data)
    if errors:
        return jsonify({"errors": errors}), 422

    category_id = None
    if data.get("category_id"):
        cat = Category.query.filter_by(id=data["category_id"]).first()
        if cat:
            category_id = cat.id

    product = Product(
        name=sanitise_string(data["name"], 255),
        slug=unique_slug(data["name"]),
        description=sanitise_string(data.get("description"), 10000),
        category_id=category_id,
        era=sanitise_string(data.get("era"), 100),
        material=sanitise_string(data.get("material"), 255),
        year=data.get("year"),
        condition=data.get("condition"),
        status=data.get("status", "draft"),
        badge=data.get("badge"),
        is_featured=bool(data.get("is_featured", False)),
        is_unique=bool(data.get("is_unique", False)),
        instagram_post_id=sanitise_string(data.get("instagram_post_id"), 255),
        instagram_post_url=sanitise_string(data.get("instagram_post_url"), 500),
    )
    db.session.add(product)
    db.session.flush()

    # Create variants
    variants = data.get("variants", [])
    if not variants and data.get("price") is not None:
        # Single-price product — create a default variant
        variants = [{"price": data["price"], "sale_price": data.get("sale_price")}]

    for v_data in variants:
        variant = ProductVariant(
            product_id=product.id,
            name=sanitise_string(v_data.get("name"), 255),
            price=float(v_data.get("price", 0)),
            sale_price=float(v_data["sale_price"]) if v_data.get("sale_price") else None,
            sku=sanitise_string(v_data.get("sku"), 100),
            stock_qty=int(v_data.get("stock_qty", 1)),
        )
        db.session.add(variant)

    db.session.commit()
    return jsonify(product.to_dict()), 201


@admin_products_bp.put("/products/<string:product_id>")
@require_admin
def admin_update_product(product_id: str):
    """PUT /api/admin/products/:id"""
    product = Product.query.filter_by(id=product_id).first()
    if not product:
        return jsonify({"error": "Product not found"}), 404

    data = request.get_json(silent=True) or {}
    errors = validate_product(data, is_update=True)
    if errors:
        return jsonify({"errors": errors}), 422

    # Updatable fields
    updatable = [
        "name", "description", "era", "material", "year", "condition",
        "badge", "is_featured", "is_unique", "instagram_post_id",
        "instagram_post_url", "status",
    ]
    for field in updatable:
        if field in data:
            setattr(product, field, data[field])

    if "category_id" in data:
        cat = Category.query.filter_by(id=data["category_id"]).first()
        product.category_id = cat.id if cat else None

    # Handle sold status automatically
    if data.get("status") == "sold" and not product.sold_at:
        product.sold_at = datetime.now(timezone.utc)
        product.archive_at = product.sold_at + timedelta(days=30)

    db.session.commit()
    return jsonify(product.to_dict())


@admin_products_bp.post("/products/<string:product_id>/mark-sold")
@require_admin
def admin_mark_sold(product_id: str):
    """POST /api/admin/products/:id/mark-sold"""
    product = Product.query.filter_by(id=product_id).first()
    if not product:
        return jsonify({"error": "Product not found"}), 404

    product.status = "sold"
    product.sold_at = datetime.now(timezone.utc)
    product.archive_at = product.sold_at + timedelta(days=30)

    # Mark all variants unavailable
    for variant in product.variants:
        variant.is_available = False

    db.session.commit()
    return jsonify(product.to_dict())


@admin_products_bp.delete("/products/<string:product_id>")
@require_admin
def admin_delete_product(product_id: str):
    """DELETE /api/admin/products/:id — soft delete by default."""
    product = Product.query.filter_by(id=product_id).first()
    if not product:
        return jsonify({"error": "Product not found"}), 404

    permanent = request.args.get("permanent") == "true"
    if permanent:
        db.session.delete(product)
    else:
        product.status = "archived"

    db.session.commit()
    return jsonify({"message": "Product deleted" if permanent else "Product archived"})


@admin_products_bp.post("/products/<string:product_id>/images")
@require_admin
def admin_upload_image(product_id: str):
    """POST /api/admin/products/:id/images — upload to Cloudinary, save URL."""
    product = Product.query.filter_by(id=product_id).first()
    if not product:
        return jsonify({"error": "Product not found"}), 404

    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400

    file = request.files["file"]

    try:
        import cloudinary.uploader
        result = cloudinary.uploader.upload(
            file,
            folder=f"midcenturist/products/{product_id}",
            transformation=[{"quality": "auto", "fetch_format": "auto"}],
        )
        url = result["secure_url"]
    except Exception as e:
        current_app.logger.error(f"Cloudinary upload failed: {e}")
        return jsonify({"error": "Image upload failed"}), 500

    # First image is primary by default
    is_primary = len(product.images) == 0
    sort_order = len(product.images)

    image = ProductImage(
        product_id=product.id,
        url=url,
        alt_text=sanitise_string(request.form.get("alt_text"), 255),
        sort_order=sort_order,
        is_primary=is_primary,
    )
    db.session.add(image)
    db.session.commit()

    return jsonify(image.to_dict()), 201


@admin_products_bp.delete("/products/<string:product_id>/images/<string:image_id>")
@require_admin
def admin_delete_image(product_id: str, image_id: str):
    """DELETE /api/admin/products/:id/images/:imgId"""
    image = ProductImage.query.filter_by(id=image_id, product_id=product_id).first()
    if not image:
        return jsonify({"error": "Image not found"}), 404

    # Delete from Cloudinary if URL is a Cloudinary URL
    try:
        if "cloudinary.com" in image.url:
            import cloudinary.uploader
            public_id = image.url.split("/upload/")[1].rsplit(".", 1)[0]
            cloudinary.uploader.destroy(public_id)
    except Exception as e:
        current_app.logger.warning(f"Cloudinary delete failed: {e}")

    db.session.delete(image)
    db.session.commit()

    # If we deleted the primary, promote the next image
    product = Product.query.filter_by(id=product_id).first()
    if product and product.images and not any(i.is_primary for i in product.images):
        product.images[0].is_primary = True
        db.session.commit()

    return jsonify({"message": "Image deleted"})
