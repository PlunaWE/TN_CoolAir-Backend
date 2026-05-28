from decimal import Decimal
from pydantic import BaseModel

from app.schemas.common import ORMBase


class OfferOut(BaseModel):
    key: str
    name: str
    price: Decimal
    badge: str | None = None
    description: str | None = None


class ProductOut(ORMBase):
    id: str
    slug: str
    name: str
    subtitle: str
    description: str
    stock: int
    room_size: str
    energy_text: str
    noise_text: str
    offers: list[OfferOut]
