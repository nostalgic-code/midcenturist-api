#!/usr/bin/env python
"""
Database seeding script for Midcenturist API
Populates the database with sample products, categories, and collections for testing
Run with: python seed.py
"""

import os
from app import create_app
from app.extensions import db
from app.models import Category, Collection, Product, ProductVariant, ProductImage, Subscriber, Review

def seed_database():
    """Seed the database with sample data"""
    app = create_app()
    
    with app.app_context():
        # Check if data already exists
        existing_categories = Category.query.first()
        if existing_categories:
            print("Database already seeded. Skipping...")
            return

        print("🌱 Seeding database...")

        # ─── Categories ──────────────────────────────────────────────────────

        categories = [
            Category(name="Living Room", slug="living-room"),
            Category(name="Dining Room", slug="dining-room"),
            Category(name="Bedroom", slug="bedroom"),
            Category(name="Decor Elements", slug="decor-elements"),
            Category(name="Creative Workspace", slug="creative-workspace"),
            Category(name="Outdoor", slug="outdoor"),
        ]
        db.session.add_all(categories)
        db.session.commit()
        print("✓ Categories created")

        # ─── Collections ──────────────────────────────────────────────────────

        collections = [
            Collection(
                name="New In",
                slug="new-in",
                description="Recently added pieces",
                is_active=True
            ),
            Collection(
                name="Summer Sale",
                slug="summer-sale",
                description="Selected items on sale this summer",
                is_active=True
            ),
            Collection(
                name="Scandinavian Design",
                slug="scandinavian-design",
                description="Classic Nordic furniture and decor",
                is_active=True
            ),
        ]
        db.session.add_all(collections)
        db.session.commit()
        print("✓ Collections created")

        # ─── Products ─────────────────────────────────────────────────────────

        living_room_cat = Category.query.filter_by(slug="living-room").first()
        dining_room_cat = Category.query.filter_by(slug="dining-room").first()
        bedroom_cat = Category.query.filter_by(slug="bedroom").first()
        decor_cat = Category.query.filter_by(slug="decor-elements").first()
        workspace_cat = Category.query.filter_by(slug="creative-workspace").first()
        outdoor_cat = Category.query.filter_by(slug="outdoor").first()
        
        new_in_col = Collection.query.filter_by(slug="new-in").first()
        scandinavian_col = Collection.query.filter_by(slug="scandinavian-design").first()

        products_data = [
            {
                "name": "Teak Dining Table",
                "slug": "teak-dining-table",
                "description": "Beautiful solid teak dining table from the 1960s. Seats 6-8 people comfortably. Minor wear consistent with age.",
                "category_id": dining_room_cat.id,
                "era": "1960s",
                "material": "Solid Teak",
                "year": 1965,
                "condition": "Very Good",
                "status": "live",
                "is_featured": True,
                "price": 2500.00,
                "sale_price": None,
            },
            {
                "name": "Mid-Century Lounge Chair",
                "slug": "mid-century-lounge-chair",
                "description": "Iconic lounge chair with original upholstery. Excellent condition.",
                "category_id": living_room_cat.id,
                "era": "1950s",
                "material": "Walnut Wood",
                "year": 1955,
                "condition": "Excellent",
                "status": "live",
                "is_featured": True,
                "badge": "New In",
                "price": 1800.00,
                "sale_price": 1500.00,
            },
            {
                "name": "Minimalist Bedroom Dresser",
                "slug": "minimalist-bedroom-dresser",
                "description": "Sleek wooden dresser with clean lines. Perfect for modern minimalist interiors.",
                "category_id": bedroom_cat.id,
                "era": "1970s",
                "material": "Oak Wood",
                "year": 1972,
                "condition": "Good",
                "status": "live",
                "is_featured": False,
                "badge": "Last One",
                "price": 1200.00,
                "sale_price": None,
            },
            {
                "name": "Retro Arc Floor Lamp",
                "slug": "retro-arc-floor-lamp",
                "description": "Statement floor lamp with adjustable arm and original brass accents. Perfect for any room.",
                "category_id": decor_cat.id,
                "era": "1960s",
                "material": "Brass & Steel",
                "year": 1968,
                "condition": "Very Good",
                "status": "live",
                "is_featured": False,
                "price": 450.00,
                "sale_price": 350.00,
            },
            {
                "name": "Ceramic Wall Art",
                "slug": "ceramic-wall-art",
                "description": "Handcrafted ceramic wall hanging. Original artist signature on back.",
                "category_id": decor_cat.id,
                "era": "1970s",
                "material": "Ceramic",
                "year": 1975,
                "condition": "Excellent",
                "status": "live",
                "is_featured": True,
                "is_unique": True,
                "badge": "Sale",
                "price": 600.00,
                "sale_price": 450.00,
            },
            {
                "name": "Vintage Office Desk",
                "slug": "vintage-office-desk",
                "description": "Classic wooden desk with spacious surface. Ideal for creative workspace or home office.",
                "category_id": workspace_cat.id,
                "era": "1960s",
                "material": "Solid Wood",
                "year": 1968,
                "condition": "Good",
                "status": "live",
                "is_featured": False,
                "price": 850.00,
                "sale_price": None,
            },
            {
                "name": "Vintage Garden Chair",
                "slug": "vintage-garden-chair",
                "description": "Classic metal garden chair. Great for patios and outdoor spaces.",
                "category_id": outdoor_cat.id,
                "era": "1950s",
                "material": "Metal & Wood",
                "year": 1958,
                "condition": "Very Good",
                "status": "live",
                "is_featured": False,
                "price": 350.00,
                "sale_price": None,
            },
        ]

        for prod_data in products_data:
            price = prod_data.pop("price")
            sale_price = prod_data.pop("sale_price")
            
            product = Product(**prod_data)
            db.session.add(product)
            db.session.flush()

            # Add default variant
            variant = ProductVariant(
                product_id=product.id,
                name="Standard",
                price=price,
                sale_price=sale_price,
                stock_qty=1,
                is_available=True,
            )
            db.session.add(variant)

            # Add to collections
            if product.status == "live":
                product.collections.append(new_in_col)
                if product.era in ("1950s", "1960s"):
                    product.collections.append(scandinavian_col)

        db.session.commit()
        print("✓ Products created with variants")

        # ─── Product Images ───────────────────────────────────────────────────

        # Add placeholder images (in production, upload real images to Cloudinary)
        products = Product.query.all()
        for product in products:
            image = ProductImage(
                product_id=product.id,
                url=f"https://via.placeholder.com/600x400?text={product.name.replace(' ', '+')}",
                alt_text=f"Image of {product.name}",
                sort_order=0,
                is_primary=True,
            )
            db.session.add(image)

        db.session.commit()
        print("✓ Product images added")

        # ─── Sample Reviews ───────────────────────────────────────────────────

        reviews_data = [
            {
                "product_id": Product.query.filter_by(slug="teak-dining-table").first().id,
                "reviewer_name": "Sarah M.",
                "rating": 5,
                "comment": "Beautiful table! Exactly as described. Arrived safely.",
                "is_approved": True,
            },
            {
                "product_id": Product.query.filter_by(slug="mid-century-lounge-chair").first().id,
                "reviewer_name": "John D.",
                "rating": 4,
                "comment": "Great chair, very comfortable. Minor restoration would be perfect.",
                "is_approved": True,
            },
            {
                "product_id": Product.query.filter_by(slug="retro-floor-lamp").first().id,
                "reviewer_name": "Emma L.",
                "rating": 5,
                "comment": "Perfect statement piece! Love the vintage aesthetic.",
                "is_approved": True,
            },
        ]

        for review_data in reviews_data:
            review = Review(**review_data)
            db.session.add(review)

        db.session.commit()
        print("✓ Sample reviews created")

        # ─── Sample Subscribers ────────────────────────────────────────────────

        subscribers_data = [
            Subscriber(
                email="collector@example.com",
                first_name="Jane",
                last_name="Collector",
                phone="+27721234567",
                area="Cape Town",
                source="footer",
            ),
            Subscriber(
                email="designer@example.com",
                first_name="David",
                last_name="Designer",
                phone="+27762345678",
                area="Johannesburg",
                source="popup",
            ),
            Subscriber(
                email="vintage_lover@example.com",
                first_name="Michelle",
                last_name="Vintage",
                source="checkout",
            ),
        ]

        db.session.add_all(subscribers_data)
        db.session.commit()
        print("✓ Sample subscribers created")

        print("\n✅ Database seeding complete!\n")
        print("Sample data:")
        print(f"  • {Category.query.count()} categories")
        print(f"  • {Collection.query.count()} collections")
        print(f"  • {Product.query.count()} products (live: {Product.query.filter_by(status='live').count()})")
        print(f"  • {Review.query.count()} reviews")
        print(f"  • {Subscriber.query.count()} subscribers")
        print(f"  • {ProductImage.query.count()} product images")


if __name__ == "__main__":
    seed_database()
