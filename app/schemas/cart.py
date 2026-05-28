from decimal import Decimal
from pydantic import BaseModel

from app.schemas.common import ORMBase


class AddCartItemIn(BaseModel):
    product_slug: str
    offer_key: str
    quantity: int = 1


class UpdateCartItemIn(BaseModel):
    quantity: int


class CartItemOut(ORMBase):
    id: str
    product_id: str
    offer_key: str
    offer_name: str
    quantity: int
    unit_price: Decimal
    line_total: Decimal


class CartOut(BaseModel):
    id: str
    guest_id: str
    currency: str
    items: list[CartItemOut]
    subtotal_amount: Decimal
    total_amount: Decimal
