import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Column, DateTime, ForeignKey, Integer, Numeric, String, Text

from app.core.db import Base


class Order(Base):
    __tablename__ = "orders"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    guest_id = Column(String, nullable=False, index=True)

    customer_name = Column(String, nullable=False)
    customer_email = Column(String, nullable=False)
    customer_phone = Column(String, nullable=True)

    billing_name = Column(String, nullable=False)
    billing_line1 = Column(String, nullable=False)
    billing_line2 = Column(String, nullable=True)
    billing_city = Column(String, nullable=False)
    billing_postal_code = Column(String, nullable=False)
    billing_country = Column(String, nullable=False)

    shipping_name = Column(String, nullable=False)
    shipping_line1 = Column(String, nullable=False)
    shipping_line2 = Column(String, nullable=True)
    shipping_city = Column(String, nullable=False)
    shipping_postal_code = Column(String, nullable=False)
    shipping_country = Column(String, nullable=False)

    status = Column(String, nullable=False, default="pending_payment")
    payment_status = Column(String, nullable=False, default="pending")
    payment_provider = Column(String, nullable=False, default="telecash")
    provider_transaction_id = Column(String, nullable=True)
    provider_checkout_id = Column(String, nullable=True)
    payment_link_id = Column(String, nullable=True)
    payment_redirect_url = Column(String, nullable=True)
    payment_response_payload = Column(Text, nullable=True)

    currency = Column(String, nullable=False, default="EUR")
    subtotal_amount = Column(Numeric(10, 2), nullable=False, default=Decimal("0.00"))
    shipping_amount = Column(Numeric(10, 2), nullable=False, default=Decimal("0.00"))
    tax_amount = Column(Numeric(10, 2), nullable=False, default=Decimal("0.00"))
    total_amount = Column(Numeric(10, 2), nullable=False, default=Decimal("0.00"))
    notes = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)


class OrderItem(Base):
    __tablename__ = "order_items"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    order_id = Column(String, ForeignKey("orders.id"), nullable=False, index=True)
    product_id = Column(String, ForeignKey("products.id"), nullable=False)
    product_name = Column(String, nullable=False)
    offer_key = Column(String, nullable=False)
    offer_name = Column(String, nullable=False)
    quantity = Column(Integer, nullable=False, default=1)
    unit_price = Column(Numeric(10, 2), nullable=False)
    line_total = Column(Numeric(10, 2), nullable=False)
