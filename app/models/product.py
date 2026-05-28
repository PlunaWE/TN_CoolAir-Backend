import uuid
from decimal import Decimal

from sqlalchemy import Boolean, Column, Integer, Numeric, String, Text

from app.core.db import Base


class Product(Base):
    __tablename__ = "products"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    slug = Column(String, unique=True, nullable=False, index=True)
    name = Column(String, nullable=False)
    subtitle = Column(String, nullable=False, default="")
    description = Column(Text, nullable=False, default="")
    stock = Column(Integer, nullable=False, default=50)
    room_size = Column(String, nullable=False, default="bis 42 m²")
    energy_text = Column(String, nullable=False, default="A++ Kühlen / A+ Heizen")
    noise_text = Column(String, nullable=False, default="39 dB(A)")
    active = Column(Boolean, nullable=False, default=True)

    offer_stromvorteil_price = Column(Numeric(10, 2), nullable=False, default=Decimal("949.00"))
    offer_solo_price = Column(Numeric(10, 2), nullable=False, default=Decimal("849.00"))
