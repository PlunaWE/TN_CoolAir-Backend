import json
import logging

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.db import get_db
from app.models.product import Product
from app.schemas.cart import AddCartItemIn, CartOut, UpdateCartItemIn
from app.schemas.contact import ContactIn, ContactOut
from app.schemas.order import CheckoutIn, OrderItemOut, OrderOut
from app.schemas.product import OfferOut, ProductOut
from app.services.cart_service import CartService
from app.services.contact_service import ContactService
from app.services.order_service import OrderService
from app.services.telecash_service import TeleCashService

router = APIRouter()
logger = logging.getLogger(__name__)


def guest_id_dep(x_guest_id: str | None = Header(default=None, alias="X-Guest-Id")):
    if not x_guest_id:
        raise HTTPException(status_code=400, detail="Missing X-Guest-Id header")
    return x_guest_id


def serialize_order(order, items):
    return OrderOut(
        id=order.id,
        status=order.status,
        payment_status=order.payment_status,
        customer_name=order.customer_name,
        customer_email=order.customer_email,
        customer_phone=order.customer_phone,
        currency=order.currency,
        subtotal_amount=order.subtotal_amount,
        shipping_amount=order.shipping_amount,
        tax_amount=order.tax_amount,
        total_amount=order.total_amount,
        billing_name=order.billing_name,
        billing_line1=order.billing_line1,
        billing_line2=order.billing_line2,
        billing_city=order.billing_city,
        billing_postal_code=order.billing_postal_code,
        billing_country=order.billing_country,
        shipping_name=order.shipping_name,
        shipping_line1=order.shipping_line1,
        shipping_line2=order.shipping_line2,
        shipping_city=order.shipping_city,
        shipping_postal_code=order.shipping_postal_code,
        shipping_country=order.shipping_country,
        notes=order.notes,
        provider_transaction_id=order.provider_transaction_id,
        provider_checkout_id=order.provider_checkout_id,
        payment_redirect_url=order.payment_redirect_url,
        payment_link_id=order.payment_link_id,
        items=[
            OrderItemOut(
                id=i.id,
                product_id=i.product_id,
                product_name=i.product_name,
                offer_key=i.offer_key,
                offer_name=i.offer_name,
                quantity=i.quantity,
                unit_price=i.unit_price,
                line_total=i.line_total,
            )
            for i in items
        ],
    )


def _frontend_payment_url(path: str, order_id: str | None = None) -> str:
    base = settings.TELECASH_SUCCESS_URL

    if path == "failure":
        base = settings.TELECASH_FAIL_URL
    elif path == "cancel":
        base = settings.TELECASH_CANCEL_URL

    if order_id:
        separator = "&" if "?" in base else "?"
        return f"{base}{separator}order_id={order_id}"

    return base


async def _parse_request_payload(request: Request):
    data = dict(request.query_params)

    if request.method != "POST":
        return data

    content_type = (request.headers.get("content-type") or "").lower()

    if "application/x-www-form-urlencoded" in content_type or "multipart/form-data" in content_type:
        try:
            form = await request.form()
            data.update({k: str(v) for k, v in form.items()})
            return data
        except AssertionError:
            return data
        except Exception:
            logger.exception("Could not parse Fiserv form payload")
            return data

    try:
        body = await request.json()
        if isinstance(body, dict):
            data.update(body)
        elif isinstance(body, list):
            return body
    except Exception:
        pass

    return data


@router.get("/health")
def health():
    return {"status": "ok"}


@router.get("/products", response_model=list[ProductOut])
def list_products(db: Session = Depends(get_db)):
    products = db.query(Product).filter(Product.active.is_(True)).all()
    out = []

    for p in products:
        out.append(
            ProductOut(
                id=p.id,
                slug=p.slug,
                name=p.name,
                subtitle=p.subtitle,
                description=p.description,
                stock=p.stock,
                room_size=p.room_size,
                energy_text=p.energy_text,
                noise_text=p.noise_text,
                offers=[
                    OfferOut(
                        key="stromvorteil",
                        name="Midea Portasplit 3,5 kW + Strom-Vorteil",
                        price=p.offer_stromvorteil_price,
                        badge="LAUNCH-ANGEBOT",
                        description="150 Euro Wien Energie-Stromgutschein inklusive",
                    ),
                    OfferOut(
                        key="solo",
                        name="Midea Portasplit 3,5 kW ohne Strom-Vorteil",
                        price=p.offer_solo_price,
                    ),
                ],
            )
        )

    return out


@router.get("/products/{slug}", response_model=ProductOut)
def get_product(slug: str, db: Session = Depends(get_db)):
    p = db.query(Product).filter(Product.slug == slug, Product.active.is_(True)).first()

    if not p:
        raise HTTPException(status_code=404, detail="Product not found")

    return ProductOut(
        id=p.id,
        slug=p.slug,
        name=p.name,
        subtitle=p.subtitle,
        description=p.description,
        stock=p.stock,
        room_size=p.room_size,
        energy_text=p.energy_text,
        noise_text=p.noise_text,
        offers=[
            OfferOut(
                key="stromvorteil",
                name="Midea Portasplit 3,5 kW + Strom-Vorteil",
                price=p.offer_stromvorteil_price,
                badge="LAUNCH-ANGEBOT",
                description="150 Euro Wien Energie-Stromgutschein inklusive",
            ),
            OfferOut(
                key="solo",
                name="Midea Portasplit 3,5 kW ohne Strom-Vorteil",
                price=p.offer_solo_price,
            ),
        ],
    )


@router.get("/cart", response_model=CartOut)
def get_cart(guest_id: str = Depends(guest_id_dep), db: Session = Depends(get_db)):
    data = CartService(db).get_cart(guest_id)
    return CartOut(**data)


@router.post("/cart/items", response_model=CartOut)
def add_cart_item(
    payload: AddCartItemIn,
    guest_id: str = Depends(guest_id_dep),
    db: Session = Depends(get_db),
):
    data = CartService(db).add_item(guest_id, payload)
    return CartOut(**data)


@router.patch("/cart/items/{item_id}", response_model=CartOut)
def update_cart_item(
    item_id: str,
    payload: UpdateCartItemIn,
    guest_id: str = Depends(guest_id_dep),
    db: Session = Depends(get_db),
):
    data = CartService(db).update_item(guest_id, item_id, payload.quantity)
    return CartOut(**data)


@router.delete("/cart/items/{item_id}", response_model=CartOut)
def delete_cart_item(
    item_id: str,
    guest_id: str = Depends(guest_id_dep),
    db: Session = Depends(get_db),
):
    data = CartService(db).delete_item(guest_id, item_id)
    return CartOut(**data)


@router.delete("/cart", response_model=CartOut)
def clear_cart(guest_id: str = Depends(guest_id_dep), db: Session = Depends(get_db)):
    data = CartService(db).clear_cart(guest_id)
    return CartOut(**data)


@router.post("/checkout/start")
def start_checkout(
    payload: CheckoutIn,
    guest_id: str = Depends(guest_id_dep),
    db: Session = Depends(get_db),
):
    order, items, telecash = OrderService(db).checkout(guest_id, payload)

    return {
        "order": serialize_order(order, items),
        "payment": {
            "provider": "fiserv_checkout",
            "status": "form_ready" if telecash.get("ok") else "gateway_error",
            "redirect_url": telecash.get("redirect_url"),
            "form_action": telecash.get("action"),
            "form_fields": telecash.get("fields"),
            "gateway_payload": telecash.get("payload"),
        },
    }


@router.get("/orders/{order_id}")
def get_order(order_id: str, db: Session = Depends(get_db)):
    order, items = OrderService(db).get_order(order_id)
    return serialize_order(order, items)


@router.api_route("/payments/telecash/connect/return", methods=["GET", "POST"])
async def telecash_connect_return(
    request: Request,
    result: str | None = None,
    db: Session = Depends(get_db),
):
    payload = await _parse_request_payload(request)

    order_id = (
        payload.get("oid")
        or payload.get("merchantTransactionId")
        or payload.get("orderId")
        or payload.get("order_id")
    )

    if not order_id:
        logger.error("Fiserv return without order id. Payload: %s", payload)
        return RedirectResponse(_frontend_payment_url("failure"), status_code=303)

    payload["_result_hint"] = result or payload.get("result") or ""

    try:
        service = TeleCashService()

        if payload.get("response_hash"):
            payload["_response_hash_valid"] = service.verify_response_hash(
                payload,
                notification=False,
            )

        order, items = OrderService(db).apply_return(str(order_id), payload)

        target = "failure"
        if order.payment_status == "paid":
            target = "success"
        elif order.payment_status in {"cancelled", "canceled"}:
            target = "cancel"

        return RedirectResponse(_frontend_payment_url(target, order.id), status_code=303)

    except Exception:
        logger.exception("Fiserv return handling failed for order_id=%s payload=%s", order_id, payload)
        return RedirectResponse(_frontend_payment_url("failure", str(order_id)), status_code=303)


@router.api_route("/payments/telecash/refresh/{order_id}", methods=["GET", "POST"])
def telecash_refresh(order_id: str, db: Session = Depends(get_db)):
    order, items = OrderService(db).get_order(order_id)
    return {"ok": True, "order": serialize_order(order, items)}


@router.api_route("/payments/telecash/connect/resume/{order_id}", methods=["GET"])
def telecash_connect_resume(order_id: str, db: Session = Depends(get_db)):
    order, _ = OrderService(db).get_order(order_id)

    stored = {}
    if order.payment_response_payload:
        try:
            stored = json.loads(order.payment_response_payload)
        except Exception:
            stored = {}

    action = stored.get("action")
    fields = stored.get("fields") or {}

    if not action or not isinstance(fields, dict) or not fields:
        raise HTTPException(status_code=400, detail="Payment request is not available")

    html = TeleCashService().build_resume_html(action=action, fields=fields)
    return HTMLResponse(content=html)


@router.api_route("/payments/telecash/notify", methods=["GET", "POST"])
async def telecash_notify(request: Request, db: Session = Depends(get_db)):
    payload = await _parse_request_payload(request)
    events = payload if isinstance(payload, list) else [payload]
    processed = []
    service = TeleCashService()

    for event in events:
        if not isinstance(event, dict):
            continue

        order_id = (
            event.get("oid")
            or event.get("merchantTransactionId")
            or event.get("orderId")
            or event.get("order_id")
        )

        if not order_id:
            processed.append(
                {
                    "ok": False,
                    "message": "Missing order reference",
                    "payload": event,
                }
            )
            continue

        try:
            if event.get("notification_hash"):
                event["_notification_hash_valid"] = service.verify_response_hash(
                    event,
                    notification=True,
                )

            order, items = OrderService(db).apply_return(str(order_id), event)
            processed.append({"ok": True, "order": serialize_order(order, items)})

        except Exception as exc:
            logger.exception("Fiserv notification handling failed for order_id=%s", order_id)
            processed.append(
                {
                    "ok": False,
                    "order_id": str(order_id),
                    "message": str(exc),
                    "payload": event,
                }
            )

    return {"ok": True, "processed": processed}


@router.post("/contact", response_model=ContactOut)
def submit_contact(payload: ContactIn, db: Session = Depends(get_db)):
    return ContactService(db).submit(payload)