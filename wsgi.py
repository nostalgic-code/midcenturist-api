from app import create_app
from app.extensions import db
from sqlalchemy import text

app = create_app()

with app.app_context():
    db.create_all()

    # Add columns that db.create_all() won't add to existing tables
    migrations = [
        "ALTER TABLE product_images ADD COLUMN IF NOT EXISTS data BYTEA",
        "ALTER TABLE product_images ADD COLUMN IF NOT EXISTS content_type VARCHAR(100)",
        "ALTER TABLE product_images ADD COLUMN IF NOT EXISTS filename VARCHAR(255)",
        "ALTER TABLE product_images ALTER COLUMN url DROP NOT NULL",
        "ALTER TABLE subscribers ADD COLUMN IF NOT EXISTS phone VARCHAR(30)",
        "ALTER TABLE subscribers ADD COLUMN IF NOT EXISTS area VARCHAR(100)",
    ]
    for sql in migrations:
        try:
            db.session.execute(text(sql))
        except Exception:
            db.session.rollback()
    db.session.commit()

if __name__ == "__main__":
    app.run()
