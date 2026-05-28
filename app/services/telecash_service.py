
import base64
import hashlib
import hmac
import html
import json
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import Any
from urllib.parse import urlencode
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.core.config import settings


class TeleCashService:
    def __init__(self) -> None:
        self.connect_url = settings.TELECASH_CONNECT_URL.strip()
        self.store_name = settings.TELECASH_STORE_NAME.strip()
        self.shared_secret = settings.TELECASH_SHARED_SECRET
        self.timezone = settings.TELECASH_TIMEZONE.strip() or "Europe/Berlin"
        self.payment_method = (settings.TELECASH_PAYMENT_METHOD or "").strip()
        self.language = (settings.TELECASH_LANGUAGE or "de_DE").strip() or "de_DE"
        self.checkout_option = (settings.TELECASH_CHECKOUT_OPTION or "combinedpage").strip() or "combinedpage"
        self.checkout_mode = (settings.TELECASH_CHECKOUT_MODE or "").strip()
        self.bcountry = (settings.TELECASH_BCOUNTRY or "AT").strip() or "AT"

    def _currency_numeric(self, currency: str) -> str:
        mapping = {
            "EUR": "978",
            "USD": "840",
            "GBP": "826",
            "CHF": "756",
        }
        return mapping.get((currency or "EUR").upper(), "978")

    def _format_amount(self, amount: Any) -> str:
        if isinstance(amount, Decimal):
            value = amount
        else:
            value = Decimal(str(amount))
        return str(value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))

    def _txndatetime(self) -> str:
        try:
            return datetime.now(ZoneInfo(self.timezone)).strftime("%Y:%m:%d-%H:%M:%S")
        except ZoneInfoNotFoundError:
            # Windows often needs the tzdata package; fall back to local time instead of crashing checkout
            return datetime.now().strftime("%Y:%m:%d-%H:%M:%S")

    def _sorted_hash_string(self, fields: dict[str, str]) -> str:
        items = [(k, str(v)) for k, v in fields.items() if str(v) != "" and k != "hashExtended"]
        items.sort(key=lambda kv: kv[0])
        return "|".join(v for _, v in items)

    def _hmac_b64(self, payload_string: str) -> str:
        digest = hmac.new(
            self.shared_secret.encode("utf-8"),
            payload_string.encode("utf-8"),
            hashlib.sha256,
        ).digest()
        return base64.b64encode(digest).decode("utf-8")

    def build_connect_request(self, *, order: Any) -> dict[str, Any]:
        txndatetime = self._txndatetime()
        currency_numeric = self._currency_numeric(order.currency)
        chargetotal = self._format_amount(order.total_amount)
        base_return = settings.TELECASH_RETURN_BASE_URL.rstrip("/")
        success_return = f"{base_return}?result=success"
        fail_return = f"{base_return}?result=failure"

        fields: dict[str, str] = {
            "txntype": "sale",
            "timezone": self.timezone,
            "txndatetime": txndatetime,
            "hash_algorithm": "HMACSHA256",
            "storename": self.store_name,
            "checkoutoption": self.checkout_option,
            "oid": order.id,
            "chargetotal": chargetotal,
            "currency": currency_numeric,
            "responseSuccessURL": success_return,
            "responseFailURL": fail_return,
            "responseURL": success_return,
            "language": self.language,
            "bname": order.customer_name,
            "email": order.customer_email,
            "bcountry": self.bcountry,
        }

        if self.checkout_mode:
            fields["mode"] = self.checkout_mode
        if self.payment_method:
            fields["paymentMethod"] = self.payment_method

        notification = (settings.TELECASH_NOTIFICATION_URL or "").strip()
        if notification.lower().startswith("https://"):
            fields["transactionNotificationURL"] = notification

        fields["hashExtended"] = self._hmac_b64(self._sorted_hash_string(fields))

        resume_url = f"{base_return.rsplit('/return', 1)[0]}/resume/{order.id}"
        return {
            "ok": True,
            "status_code": 200,
            "payload": {
                "provider": "telecash_connect",
                "action": self.connect_url,
                "fields": fields,
                "txndatetime": txndatetime,
            },
            "redirect_url": resume_url,
            "payment_link_id": None,
            "action": self.connect_url,
            "fields": fields,
            "txndatetime": txndatetime,
        }

    def verify_response_hash(self, payload: dict[str, Any], *, notification: bool = False) -> bool:
        hash_field = "notification_hash" if notification else "response_hash"
        received = str(payload.get(hash_field) or "").strip()
        if not received:
            return False
        required = [
            str(payload.get("approval_code") or ""),
            str(payload.get("chargetotal") or ""),
            str(payload.get("currency") or ""),
            str(payload.get("txndatetime") or payload.get("hiddenTxndatetime") or ""),
            str(payload.get("storename") or payload.get("hiddenStorename") or self.store_name),
        ]
        if not all(required):
            return False
        expected = self._hmac_b64("|".join(required))
        return hmac.compare_digest(received, expected)

    def build_resume_html(self, *, action: str, fields: dict[str, Any]) -> str:
        inputs = "\n".join(
            f'<input type="hidden" name="{html.escape(str(k))}" value="{html.escape(str(v))}" />'
            for k, v in fields.items()
        )
        return f"""<!DOCTYPE html>
<html lang="de">
<head>
  <meta charset="utf-8" />
  <title>Zahlungsseite wird geöffnet</title>
  <meta name="viewport" content="width=device-width,initial-scale=1" />
</head>
<body style="font-family:Arial,sans-serif;padding:24px;">
  <p>Zahlungsseite wird geöffnet...</p>
  <form id="telecash-connect-form" method="post" action="{html.escape(action)}">{inputs}</form>
  <script>document.getElementById('telecash-connect-form').submit();</script>
</body>
</html>"""


    @staticmethod
    def sanitize_fields(fields: dict[str, str]) -> dict[str, str]:
        hidden = {"hashExtended"}
        return {k: ("***" if k in hidden else str(v)) for k, v in fields.items()}
