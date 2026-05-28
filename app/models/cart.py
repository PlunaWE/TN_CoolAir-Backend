import uuid
from decimal import Decimal
from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import relationship

from app.core.db import Base


class Cart(Base):
    __tablename__ = "carts"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    guest_id = Column(String, unique=True, nullable=False, index=True)
    currency = Column(String, nullable=False, default="EUR")
    created_at = Column(DateTime, default=datetime.utcnow)

    items = relationship("CartItem", cascade="all, delete-orphan")


class CartItem(Base):
    __tablename__ = "cart_items"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    cart_id = Column(String, ForeignKey("carts.id"), nullable=False, index=True)
    product_id = Column(String, ForeignKey("products.id"), nullable=False)
    offer_key = Column(String, nullable=False)
    offer_name = Column(String, nullable=False)
    quantity = Column(Integer, nullable=False, default=1)
    unit_price = Column(Numeric(10, 2), nullable=False, default=Decimal("0.00"))
    line_total = Column(Numeric(10, 2), nullable=False, default=Decimal("0.00"))
