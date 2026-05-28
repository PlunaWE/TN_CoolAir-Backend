from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.cart import Cart, CartItem
from app.models.product import Product


def build_offer_payload(product: Product, offer_key: str) -> tuple[str, Decimal]:
    if offer_key == "stromvorteil":
        return "Midea Portasplit 3,5 kW + Strom-Vorteil", product.offer_stromvorteil_price
    if offer_key == "solo":
        return "Midea Portasplit 3,5 kW ohne Strom-Vorteil", product.offer_solo_price
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unknown offer key")


class CartService:
    def __init__(self, db: Session):
        self.db = db

    def _get_or_create_cart(self, guest_id: str) -> Cart:
        cart = self.db.query(Cart).filter(Cart.guest_id == guest_id).first()
        if not cart:
            cart = Cart(guest_id=guest_id, currency="EUR")
            self.db.add(cart)
            self.db.flush()
        return cart

    def _serialize(self, cart: Cart):
        items = self.db.query(CartItem).filter(CartItem.cart_id == cart.id).all()
        subtotal = sum((item.line_total for item in items), Decimal("0.00"))
        return {
            "id": cart.id,
            "guest_id": cart.guest_id,
            "currency": cart.currency,
            "items": items,
            "subtotal_amount": subtotal,
            "total_amount": subtotal,
        }

    def get_cart(self, guest_id: str):
        cart = self._get_or_create_cart(guest_id)
        return self._serialize(cart)

    def add_item(self, guest_id: str, payload):
        cart = self._get_or_create_cart(guest_id)
        product = self.db.query(Product).filter(Product.slug == payload.product_slug, Product.active.is_(True)).first()
        if not product:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")

        offer_name, price = build_offer_payload(product, payload.offer_key)

        existing = (
            self.db.query(CartItem)
            .filter(CartItem.cart_id == cart.id, CartItem.product_id == product.id, CartItem.offer_key == payload.offer_key)
            .first()
        )
        qty = max(1, payload.quantity)
        if existing:
            existing.quantity = qty
            existing.unit_price = price
            existing.offer_name = offer_name
            existing.line_total = price * qty
        else:
            existing = CartItem(
                cart_id=cart.id,
                product_id=product.id,
                offer_key=payload.offer_key,
                offer_name=offer_name,
                quantity=qty,
                unit_price=price,
                line_total=price * qty,
            )
            self.db.add(existing)

        self.db.commit()
        self.db.refresh(cart)
        return self._serialize(cart)

    def update_item(self, guest_id: str, item_id: str, quantity: int):
        cart = self._get_or_create_cart(guest_id)
        item = self.db.query(CartItem).filter(CartItem.id == item_id, CartItem.cart_id == cart.id).first()
        if not item:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cart item not found")
        item.quantity = max(1, quantity)
        item.line_total = item.unit_price * item.quantity
        self.db.commit()
        return self._serialize(cart)

    def delete_item(self, guest_id: str, item_id: str):
        cart = self._get_or_create_cart(guest_id)
        item = self.db.query(CartItem).filter(CartItem.id == item_id, CartItem.cart_id == cart.id).first()
        if not item:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cart item not found")
        self.db.delete(item)
        self.db.commit()
        return self._serialize(cart)

    def clear_cart(self, guest_id: str):
        cart = self._get_or_create_cart(guest_id)
        self.db.query(CartItem).filter(CartItem.cart_id == cart.id).delete()
        self.db.commit()
        return self._serialize(cart)
