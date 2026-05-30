import json
import logging
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.cart import Cart, CartItem
from app.models.order import Order, OrderItem
from app.models.product import Product
from app.services.email_service import EmailService
from app.services.telecash_service import TeleCashService

logger = logging.getLogger(__name__)

MAX_SOLD_DEVICES = 50
LIMIT_REACHED_MESSAGE = "Der Kauf dieses Produkts ist aktuell nicht möglich."


class OrderService:
    def __init__(self, db: Session):
        self.db = db

    def _sold_devices_count(self, exclude_order_id: str | None = None) -> int:
        query = (
            self.db.query(OrderItem.quantity)
            .join(Order, Order.id == OrderItem.order_id)
            .filter((Order.payment_status == "paid") | (Order.status == "paid"))
        )

        if exclude_order_id:
            query = query.filter(Order.id != exclude_order_id)

        sold_rows = query.all()
        return sum(int(row[0] or 0) for row in sold_rows)

    def _ensure_sale_capacity(
        self,
        additional_quantity: int,
        exclude_order_id: str | None = None,
    ) -> None:
        sold_devices = self._sold_devices_count(exclude_order_id=exclude_order_id)

        if sold_devices + int(additional_quantity or 0) > MAX_SOLD_DEVICES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=LIMIT_REACHED_MESSAGE,
            )

    def checkout(self, guest_id: str, payload):
        allowed_countries = {"AT", "AUSTRIA", "ÖSTERREICH", "OESTERREICH"}
        billing_country = (payload.billing_country or "").strip().upper()
        shipping_country = (payload.shipping_country or "").strip().upper()

        if billing_country not in allowed_countries or shipping_country not in allowed_countries:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Aktuell liefern wir nur nach Österreich.",
            )

        if not getattr(payload, "accept_terms", False):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Bitte akzeptieren Sie die AGB und Datenschutzbestimmungen.",
            )

        if not getattr(payload, "accept_installation_ack", False):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Bitte bestätigen Sie den Hinweis zur Montage.",
            )

        cart = self.db.query(Cart).filter(Cart.guest_id == guest_id).first()
        if not cart:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cart is empty")

        cart_items = self.db.query(CartItem).filter(CartItem.cart_id == cart.id).all()
        if not cart_items:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cart is empty")

        requested_quantity = sum(int(ci.quantity or 0) for ci in cart_items)
        self._ensure_sale_capacity(requested_quantity)

        subtotal = Decimal("0.00")
        shipping_fee = Decimal("79.00")

        order = Order(
            guest_id=guest_id,
            customer_name=payload.customer_name,
            customer_email=payload.customer_email,
            customer_phone=payload.customer_phone,
            billing_name=payload.billing_name,
            billing_line1=payload.billing_line1,
            billing_line2=payload.billing_line2,
            billing_city=payload.billing_city,
            billing_postal_code=payload.billing_postal_code,
            billing_country="AT",
            shipping_name=payload.shipping_name,
            shipping_line1=payload.shipping_line1,
            shipping_line2=payload.shipping_line2,
            shipping_city=payload.shipping_city,
            shipping_postal_code=payload.shipping_postal_code,
            shipping_country="AT",
            status="pending_payment",
            payment_status="pending",
            payment_provider="fiserv_checkout",
            currency=cart.currency,
            subtotal_amount=Decimal("0.00"),
            shipping_amount=shipping_fee,
            tax_amount=Decimal("0.00"),
            total_amount=Decimal("0.00"),
            notes=payload.notes,
        )

        self.db.add(order)
        self.db.flush()

        items_out = []

        for ci in cart_items:
            product = self.db.query(Product).filter(Product.id == ci.product_id).first()

            if not product:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Missing product",
                )

            if product.stock < ci.quantity:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Insufficient stock for {product.name}",
                )

            line_total = ci.unit_price * ci.quantity
            subtotal += line_total

            oi = OrderItem(
                order_id=order.id,
                product_id=product.id,
                product_name=product.name,
                offer_key=ci.offer_key,
                offer_name=ci.offer_name,
                quantity=ci.quantity,
                unit_price=ci.unit_price,
                line_total=line_total,
            )

            self.db.add(oi)
            items_out.append(oi)

        order.subtotal_amount = subtotal
        order.shipping_amount = shipping_fee
        order.total_amount = subtotal + shipping_fee

        for ci in cart_items:
            self.db.delete(ci)

        connect_data = TeleCashService().build_connect_request(order=order)

        order.payment_response_payload = json.dumps(connect_data.get("payload", {}))
        order.payment_redirect_url = connect_data.get("redirect_url")
        order.payment_link_id = connect_data.get("payment_link_id")
        order.provider_checkout_id = (
            connect_data.get("checkout_id")
            or connect_data.get("payment_link_id")
            or connect_data.get("txndatetime")
        )
        order.provider_transaction_id = None
        order.payment_status = "pending_payment" if connect_data.get("ok") else "gateway_error"

        self.db.commit()
        self.db.refresh(order)

        return order, items_out, connect_data

    def apply_stock_for_paid_order(self, order_id: str):
        order = self.db.query(Order).filter(Order.id == order_id).first()

        if not order:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")

        items = self.db.query(OrderItem).filter(OrderItem.order_id == order.id).all()
        requested_quantity = sum(int(item.quantity or 0) for item in items)

        # Exclude this order from the max-sold calculation, otherwise a newly paid
        # order is counted twice. Yes, that was a very stupid little trap.
        self._ensure_sale_capacity(requested_quantity, exclude_order_id=order.id)

        for item in items:
            product = self.db.query(Product).filter(Product.id == item.product_id).first()

            if not product:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Missing product for item {item.product_name}",
                )

            if product.stock < item.quantity:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Insufficient stock for {item.product_name}",
                )

            product.stock -= item.quantity

        self.db.flush()
        return order, items

    def send_confirmation_email(self, order: Order) -> None:
        EmailService().send_order_confirmation(
            to_email=order.customer_email,
            customer_name=order.customer_name,
            order_id=order.id,
            total_amount=str(order.total_amount),
            currency=order.currency,
        )

    def send_provider_notification(self, order: Order, items: list[OrderItem]) -> None:
        EmailService().send_provider_notification(
            order_id=order.id,
            customer_name=order.customer_name,
            customer_email=order.customer_email,
            customer_phone=order.customer_phone,
            shipping_name=order.shipping_name,
            shipping_line1=order.shipping_line1,
            shipping_line2=order.shipping_line2,
            shipping_city=order.shipping_city,
            shipping_postal_code=order.shipping_postal_code,
            shipping_country=order.shipping_country,
            total_amount=str(order.total_amount),
            currency=order.currency,
            notes=order.notes,
            items=[
                {
                    "offer_name": item.offer_name,
                    "quantity": item.quantity,
                    "line_total": str(item.line_total),
                }
                for item in items
            ],
        )

    def apply_return(self, order_id: str, payload: dict):
        order = self.db.query(Order).filter(Order.id == order_id).first()

        if not order:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")

        items = self.db.query(OrderItem).filter(OrderItem.order_id == order.id).all()
        was_paid_before = order.payment_status == "paid" or order.status == "paid"

        try:
            order.payment_response_payload = json.dumps(payload)
        except Exception:
            order.payment_response_payload = json.dumps({"raw": str(payload)})

        result_hint = str(payload.get("_result_hint") or payload.get("result") or "").lower()

        approval_code = str(payload.get("approval_code") or "")
        status_value = str(
            payload.get("status")
            or payload.get("ipgTransactionStatus")
            or payload.get("transactionStatus")
            or payload.get("transactionResult")
            or ""
        ).upper()
        event_type = str(payload.get("type") or "").lower()

        is_success = (
            result_hint == "success"
            or approval_code.startswith("Y")
            or status_value in {"APPROVED", "SUCCESS", "SUCCEEDED", "COMPLETED", "CAPTURED"}
            or event_type.endswith(".success")
        )

        is_failed = (
            result_hint == "failure"
            or approval_code.startswith("N")
            or status_value in {"DECLINED", "FAILED", "FAILURE", "REJECTED"}
            or event_type.endswith(".failure")
            or event_type.endswith(".failed")
        )

        is_cancelled = (
            result_hint in {"cancel", "cancelled", "canceled"}
            or str(payload.get("cancelled")).lower() in {"true", "1"}
            or event_type.endswith(".cancelled")
            or event_type.endswith(".canceled")
        )

        is_pending = approval_code.startswith("?") or status_value in {"WAITING", "PENDING"}

        if payload.get("ipgTransactionId"):
            order.provider_transaction_id = str(payload.get("ipgTransactionId"))
        elif payload.get("hppTransactionId"):
            order.provider_transaction_id = str(payload.get("hppTransactionId"))
        elif payload.get("checkoutId"):
            order.provider_transaction_id = str(payload.get("checkoutId"))
        elif payload.get("checkout_id"):
            order.provider_transaction_id = str(payload.get("checkout_id"))

        if is_success:
            order.payment_status = "paid"
            order.status = "paid"

            # Commit paid status first. The frontend polling should see success even if
            # stock/email handling has its own little meltdown.
            self.db.commit()
            self.db.refresh(order)

            if not was_paid_before:
                try:
                    self.apply_stock_for_paid_order(order.id)
                    self.db.commit()
                    self.db.refresh(order)
                except Exception:
                    self.db.rollback()
                    logger.exception("Stock update failed for paid order_id=%s", order.id)

                try:
                    self.send_confirmation_email(order)
                except Exception:
                    logger.exception("Customer confirmation email failed for order_id=%s", order.id)

                try:
                    self.send_provider_notification(order, items)
                except Exception:
                    logger.exception("Provider notification email failed for order_id=%s", order.id)

        elif is_cancelled:
            order.payment_status = "cancelled"
            order.status = "cancelled"
            self.db.commit()
            self.db.refresh(order)

        elif is_failed:
            order.payment_status = "failed"
            order.status = "payment_failed"
            self.db.commit()
            self.db.refresh(order)

        elif is_pending:
            order.payment_status = "pending"
            order.status = "pending_payment"
            self.db.commit()
            self.db.refresh(order)

        else:
            # Unknown provider return. Do not crash; store the payload and keep status.
            order.payment_status = order.payment_status or "pending"
            order.status = order.status or "pending_payment"
            self.db.commit()
            self.db.refresh(order)

        items = self.db.query(OrderItem).filter(OrderItem.order_id == order.id).all()
        return order, items

    def get_order(self, order_id: str):
        order = self.db.query(Order).filter(Order.id == order_id).first()

        if not order:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")

        items = self.db.query(OrderItem).filter(OrderItem.order_id == order.id).all()
        return order, items