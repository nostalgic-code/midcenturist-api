from flask import Flask
from config import config
from app.extensions import db, migrate, cors, limiter, talisman
import os


def create_app(config_name: str = None) -> Flask:
    if config_name is None:
        config_name = os.environ.get("FLASK_ENV", "development")

    app = Flask(__name__)
    app.config.from_object(config[config_name])

    # Call init_app for production fixes (postgres:// → postgresql://)
    if hasattr(config[config_name], "init_app"):
        config[config_name].init_app(app)

    # Extensions
    db.init_app(app)
    migrate.init_app(app, db)

    cors.init_app(
        app,
        resources={r"/api/*": {"origins": app.config["ALLOWED_ORIGINS"]}},
        supports_credentials=True,
    )

    limiter.init_app(app)

    # Security headers — relaxed for API (no CSP needed, no HTML responses)
    talisman.init_app(
        app,
        force_https=not app.debug,
        content_security_policy=False,
        strict_transport_security=not app.debug,
        referrer_policy="strict-origin-when-cross-origin",
    )

    # Register blueprints
    from app.routes.products import products_bp
    from app.routes.categories import categories_bp
    from app.routes.cart import cart_bp
    from app.routes.orders import orders_bp
    # from app.routes.payments import payments_bp  # TODO: Enable after payment gateway is decided
    from app.routes.newsletter import newsletter_bp
    from app.routes.admin.products import admin_products_bp
    from app.routes.admin.orders import admin_orders_bp, admin_categories_bp, admin_instagram_bp, admin_reviews_bp
    from app.routes.admin.auth import admin_auth_bp

    app.register_blueprint(products_bp, url_prefix="/api")
    app.register_blueprint(categories_bp, url_prefix="/api")
    app.register_blueprint(cart_bp, url_prefix="/api")
    app.register_blueprint(orders_bp, url_prefix="/api")
    # app.register_blueprint(payments_bp, url_prefix="/api/payments")  # TODO: Enable after payment gateway is decided
    app.register_blueprint(newsletter_bp, url_prefix="/api")
    app.register_blueprint(admin_auth_bp, url_prefix="/api/admin")
    app.register_blueprint(admin_products_bp, url_prefix="/api/admin")
    app.register_blueprint(admin_orders_bp, url_prefix="/api/admin")
    app.register_blueprint(admin_categories_bp, url_prefix="/api/admin")
    app.register_blueprint(admin_instagram_bp, url_prefix="/api/admin")
    app.register_blueprint(admin_reviews_bp, url_prefix="/api/admin")

    # Health check
    @app.get("/api/health")
    def health():
        return {"status": "ok", "env": config_name}

    return app
