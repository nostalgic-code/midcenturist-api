from flask import Blueprint, jsonify
from app.extensions import limiter
from app.models import Category, Collection, Product

categories_bp = Blueprint("categories", __name__)


@categories_bp.get("/categories")
@limiter.limit("60 per minute")
def list_categories():
    """GET /api/categories — full tree with product counts."""
    top_level = Category.query.filter_by(parent_id=None).all()

    def build_node(cat):
        count = Product.query.filter_by(category_id=cat.id, status="live").count()
        node = cat.to_dict()
        node["product_count"] = count
        node["children"] = [build_node(c) for c in cat.children]
        return node

    return jsonify({"categories": [build_node(c) for c in top_level]})


@categories_bp.get("/categories/<string:slug>/products")
@limiter.limit("60 per minute")
def category_products(slug: str):
    """GET /api/categories/:slug/products"""
    cat = Category.query.filter_by(slug=slug).first()
    if not cat:
        return jsonify({"error": "Category not found"}), 404

    # Include child categories
    cat_ids = [cat.id] + [c.id for c in cat.children]
    products = Product.query.filter(
        Product.category_id.in_(cat_ids),
        Product.status == "live"
    ).order_by(Product.created_at.desc()).all()

    return jsonify({
        "category": cat.to_dict(),
        "products": [p.to_dict() for p in products],
        "total": len(products),
    })


@categories_bp.get("/collections")
@limiter.limit("60 per minute")
def list_collections():
    """GET /api/collections"""
    collections = Collection.query.filter_by(is_active=True).all()
    return jsonify({"collections": [c.to_dict() for c in collections]})


@categories_bp.get("/collections/<string:slug>/products")
@limiter.limit("60 per minute")
def collection_products(slug: str):
    """GET /api/collections/:slug/products"""
    col = Collection.query.filter_by(slug=slug, is_active=True).first()
    if not col:
        return jsonify({"error": "Collection not found"}), 404

    products = [p for p in col.products if p.status == "live"]

    return jsonify({
        "collection": col.to_dict(),
        "products": [p.to_dict() for p in products],
        "total": len(products),
    })
