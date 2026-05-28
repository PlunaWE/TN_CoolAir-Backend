from decimal import Decimal
from pydantic import BaseModel

from app.schemas.common import ORMBase


class CheckoutIn(BaseModel):
    customer_name: str
    customer_email: str
    customer_phone: str | None = None
    billing_name: str
    billing_line1: str
    billing_line2: str | None = None
    billing_city: str
    billing_postal_code: str
    billing_country: str
    shipping_name: str
    shipping_line1: str
    shipping_line2: str | None = None
    shipping_city: str
    shipping_postal_code: str
    shipping_country: str
    notes: str | None = None
    accept_terms: bool = False
    accept_installation_ack: bool = False


class OrderItemOut(ORMBase):
    id: str
    product_id: str
    product_name: str
    offer_key: str
    offer_name: str
    quantity: int
    unit_price: Decimal
    line_total: Decimal


class OrderOut(ORMBase):
    id: str
    status: str
    payment_status: str
    customer_name: str
    customer_email: str
    customer_phone: str | None
    currency: str
    subtotal_amount: Decimal
    shipping_amount: Decimal
    tax_amount: Decimal
    total_amount: Decimal
    billing_name: str
    billing_line1: str
    billing_line2: str | None
    billing_city: str
    billing_postal_code: str
    billing_country: str
    shipping_name: str
    shipping_line1: str
    shipping_line2: str | None
    shipping_city: str
    shipping_postal_code: str
    shipping_country: str
    notes: str | None
    provider_transaction_id: str | None
    provider_checkout_id: str | None
    payment_redirect_url: str | None
    payment_link_id: str | None
    items: list[OrderItemOut]
