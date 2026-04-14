from flask import Blueprint, request, jsonify
from app.extensions import db, limiter
from app.models import Product, Category, Collection
from sqlalchemy import or_

products_bp = Blueprint("products", __name__)


@products_bp.get("/products")
@limiter.limit("60 per minute")
def list_products():
    """
    GET /api/products
    Query params:
      category=slug
      collection=slug
      status=live (default)
      featured=true
      badge=New In|Last One|Sale
      page=1
      limit=24
    """
    q = Product.query

    # Default to live products only on public endpoint
    status = request.args.get("status", "live")
    q = q.filter(Product.status == status)

    category_slug = request.args.get("category")
    if category_slug:
        cat = Category.query.filter_by(slug=category_slug).first()
        if cat:
            q = q.filter(Product.category_id == cat.id)
        else:
            return jsonify({"products": [], "total": 0})

    collection_slug = request.args.get("collection")
    if collection_slug:
        col = Collection.query.filter_by(slug=collection_slug).first()
        if col:
            q = q.filter(Product.collections.any(id=col.id))

    if request.args.get("featured") == "true":
        q = q.filter(Product.is_featured == True)

    badge = request.args.get("badge")
    if badge:
        q = q.filter(Product.badge == badge)

    try:
        page = max(1, int(request.args.get("page", 1)))
        limit = min(48, max(1, int(request.args.get("limit", 24))))
    except ValueError:
        page, limit = 1, 24

    total = q.count()
    products = q.order_by(Product.created_at.desc()).offset((page - 1) * limit).limit(limit).all()

    return jsonify({
        "products": [p.to_dict(include_reviews=False) for p in products],
        "total": total,
        "page": page,
        "limit": limit,
        "pages": (total + limit - 1) // limit,
    })


@products_bp.get("/products/search")
@limiter.limit("30 per minute")
def search_products():
    """GET /api/products/search?q=teak+sideboard"""
    q_str = request.args.get("q", "").strip()
    if not q_str or len(q_str) < 2:
        return jsonify({"products": [], "total": 0})

    # PostgreSQL full-text search using ILIKE for simplicity
    # Upgrade to tsvector index in production if needed
    search = f"%{q_str}%"
    results = Product.query.filter(
        Product.status == "live",
        or_(
            Product.name.ilike(search),
            Product.description.ilike(search),
            Product.material.ilike(search),
            Product.era.ilike(search),
        )
    ).limit(20).all()

    return jsonify({
        "products": [p.to_dict() for p in results],
        "total": len(results),
        "query": q_str,
    })


@products_bp.get("/products/<string:slug>")
@limiter.limit("120 per minute")
def get_product(slug: str):
    """GET /api/products/:slug"""
    product = Product.query.filter_by(slug=slug).first()

    if not product:
        return jsonify({"error": "Product not found"}), 404

    if product.status == "archived":
        return jsonify({"error": "Product no longer available"}), 410

    return jsonify(product.to_dict(include_reviews=True))
