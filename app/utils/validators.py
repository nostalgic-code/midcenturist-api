import re
from typing import Any


EMAIL_RE = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")
PHONE_RE = re.compile(r"^[\d\s\+\-\(\)]{7,20}$")

VALID_PRODUCT_STATUSES = {"live", "draft", "sold", "archived"}
VALID_ORDER_STATUSES = {"pending", "confirmed", "paid", "shipped", "collected", "delivered", "cancelled"}
VALID_FULFILLMENT_TYPES = {"collection", "shipping"}
VALID_CONDITIONS = {"Excellent", "Very Good", "Good", "Restored"}
VALID_BADGES = {"New In", "Last One", "Sale"}
VALID_UPCOMING_STATUSES = {"coming-soon", "sourced", "in-restoration", "expected-this-week"}


def is_valid_email(email: str) -> bool:
    return bool(EMAIL_RE.match(email.strip())) if email else False


def is_valid_phone(phone: str) -> bool:
    return bool(PHONE_RE.match(phone.strip())) if phone else False


def validate_checkout(data: dict) -> list:
    """Validate checkout / order creation payload. Returns list of error strings."""
    errors = []

    billing = data.get("billing_address", {})
    if not billing.get("name"):
        errors.append("billing_address.name is required")
    if not is_valid_email(billing.get("email", "")):
        errors.append("billing_address.email is invalid")
    if not is_valid_phone(billing.get("phone", "")):
        errors.append("billing_address.phone is invalid")

    ft = data.get("fulfillment_type", "")
    if ft not in VALID_FULFILLMENT_TYPES:
        errors.append(f"fulfillment_type must be one of: {', '.join(VALID_FULFILLMENT_TYPES)}")

    if ft == "shipping":
        sa = data.get("shipping_address", {})
        if not sa.get("address_line1"):
            errors.append("shipping_address.address_line1 is required for shipping orders")
        if not sa.get("city"):
            errors.append("shipping_address.city is required for shipping orders")

    if not data.get("session_id"):
        errors.append("session_id is required")

    return errors


def validate_product(data: dict, is_update: bool = False) -> list:
    """Validate admin product create/update payload."""
    errors = []

    if not is_update:
        if not data.get("name"):
            errors.append("name is required")

    status = data.get("status")
    if status and status not in VALID_PRODUCT_STATUSES:
        errors.append(f"status must be one of: {', '.join(VALID_PRODUCT_STATUSES)}")

    condition = data.get("condition")
    if condition and condition not in VALID_CONDITIONS:
        errors.append(f"condition must be one of: {', '.join(VALID_CONDITIONS)}")

    badge = data.get("badge")
    if badge and badge not in VALID_BADGES:
        errors.append(f"badge must be one of: {', '.join(VALID_BADGES)}")

    price = data.get("price")
    if price is not None:
        try:
            p = float(price)
            if p < 0:
                errors.append("price cannot be negative")
        except (ValueError, TypeError):
            errors.append("price must be a number")

    return errors


def validate_review(data: dict) -> list:
    errors = []
    if not data.get("reviewer_name"):
        errors.append("reviewer_name is required")
    rating = data.get("rating")
    if rating is None or not isinstance(rating, int) or not (1 <= rating <= 5):
        errors.append("rating must be an integer between 1 and 5")
    return errors


def sanitise_string(val: Any, max_length: int = 500) -> str | None:
    if val is None:
        return None
    return str(val).strip()[:max_length]
