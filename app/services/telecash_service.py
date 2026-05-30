import base64
import hashlib
import hmac
import html
import json
import time
import uuid
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

import requests
import urllib3

from app.core.config import settings

# LOCAL SANDBOX ONLY.
# This avoids corporate proxy/self-signed certificate issues during local testing.
# Do NOT keep verify=False / disabled warnings for production.
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class TeleCashService:
    """
    Fiserv / TeleCash sandbox Checkout Solution integration.

    Flow:
      1. Backend creates a checkout transaction.
      2. Fiserv returns checkout.redirectionUrl.
      3. Frontend opens that URL in a new tab.

    Keep TELECASH_BASE_URL as:
      https://prod.emea.api.fiservapps.com/sandbox

    Do not include /exp/v1 in the .env value.
    """

    def __init__(self) -> None:
        self.base_url = (
            (getattr(settings, "TELECASH_BASE_URL", "") or "")
            .strip()
            .strip('"')
            .strip("'")
            .rstrip("/")
        )
        self.api_key = (
            (getattr(settings, "TELECASH_API_KEY", "") or "")
            .strip()
            .strip('"')
            .strip("'")
        )
        self.api_secret = (
            getattr(settings, "TELECASH_API_SECRET", "") or ""
        ).strip().strip('"').strip("'")
        self.store_id = (
            (getattr(settings, "TELECASH_STORE_ID", "") or "")
            .strip()
            .strip('"')
            .strip("'")
        )

    def _format_amount_decimal(self, amount: Any) -> Decimal:
        value = amount if isinstance(amount, Decimal) else Decimal(str(amount))
        return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    def _format_amount_number(self, amount: Any) -> float:
        return float(self._format_amount_decimal(amount))

    def _hmac_b64(self, payload_string: str, *, secret: str | None = None) -> str:
        digest = hmac.new(
            (secret if secret is not None else self.api_secret).encode("utf-8"),
            payload_string.encode("utf-8"),
            hashlib.sha256,
        ).digest()
        return base64.b64encode(digest).decode("utf-8")

    def _checkout_create_url(self) -> str:
        """
        Fiserv sandbox checkout endpoint.

        TELECASH_BASE_URL should be:
          https://prod.emea.api.fiservapps.com/sandbox

        Final endpoint becomes:
          https://prod.emea.api.fiservapps.com/sandbox/exp/v1/
        """
        if not self.base_url:
            raise ValueError("TELECASH_BASE_URL is required for Fiserv Checkout.")

        base = self.base_url.rstrip("/")

        if base.endswith("/exp/v1"):
            return f"{base}/checkouts"

        return f"{base}/exp/v1/checkouts"

    def _backend_return_url(self, result: str, order_id: str) -> str:
        base = settings.TELECASH_RETURN_BASE_URL.rstrip("/")
        separator = "&" if "?" in base else "?"
        return f"{base}{separator}result={result}&order_id={order_id}"

    def _json_body(self, payload: dict[str, Any]) -> str:
        return json.dumps(payload, separators=(",", ":"), ensure_ascii=False)

    def _fiserv_headers(self, body_string: str) -> dict[str, str]:
        client_request_id = str(uuid.uuid4())
        timestamp = str(int(time.time() * 1000))

        # Fiserv EMEA signature pattern:
        # Api-Key + Client-Request-Id + Timestamp + request body
        raw_signature = f"{self.api_key}{client_request_id}{timestamp}{body_string}"
        signature = self._hmac_b64(raw_signature, secret=self.api_secret)

        return {
            "Content-Type": "application/json",
            "Api-Key": self.api_key,
            "Client-Request-Id": client_request_id,
            "Timestamp": timestamp,
            "Message-Signature": signature,
        }

    def _build_checkout_payload(self, *, order: Any) -> dict[str, Any]:
        """
        Minimal checkout payload accepted by Fiserv Checkout API.

        Important:
        The sandbox schema rejects cancelUrl inside checkoutSettings.redirectBackUrls.
        Only successUrl and failureUrl are sent here.
        """
        payload: dict[str, Any] = {
            "storeId": self.store_id,
            "transactionType": "SALE",
            "transactionOrigin": "ECOM",
            "merchantTransactionId": order.id,
            "transactionAmount": {
                "currency": order.currency or "EUR",
                "total": self._format_amount_number(order.total_amount),
            },
            "checkoutSettings": {
                "locale": "de_DE",
                "redirectBackUrls": {
                    "successUrl": self._backend_return_url("success", order.id),
                    "failureUrl": self._backend_return_url("failure", order.id),
                },
            },
        }

        notification_url = (settings.TELECASH_NOTIFICATION_URL or "").strip()

        # Fiserv cannot call localhost. Only send webhook URL if it is public HTTPS.
        if notification_url and notification_url.startswith("https://"):
            payload["checkoutSettings"]["webHooksUrl"] = notification_url

        return payload

    def _find_checkout_redirect_url(self, value: Any) -> str | None:
        if not isinstance(value, dict):
            return None

        checkout = value.get("checkout")
        if isinstance(checkout, dict):
            redirect = (
                checkout.get("redirectionUrl")
                or checkout.get("redirectionURL")
                or checkout.get("redirectUrl")
                or checkout.get("redirectURL")
            )
            if isinstance(redirect, str) and redirect.startswith(("http://", "https://")):
                return redirect

        return self._find_any_url(value)

    def _find_checkout_id(self, value: Any) -> str | None:
        if not isinstance(value, dict):
            return None

        checkout = value.get("checkout")
        if isinstance(checkout, dict):
            checkout_id = (
                checkout.get("checkoutId")
                or checkout.get("checkoutID")
                or checkout.get("id")
            )
            if checkout_id:
                return str(checkout_id)

        candidates = [
            value.get("checkoutId"),
            value.get("checkoutID"),
            value.get("transactionId"),
            value.get("ipgTransactionId"),
            value.get("id"),
            value.get("orderId"),
        ]

        for candidate in candidates:
            if candidate:
                return str(candidate)

        for nested_value in value.values():
            if isinstance(nested_value, dict):
                found = self._find_checkout_id(nested_value)
                if found:
                    return found
            elif isinstance(nested_value, list):
                for item in nested_value:
                    if isinstance(item, dict):
                        found = self._find_checkout_id(item)
                        if found:
                            return found

        return None

    def _find_any_url(self, value: Any) -> str | None:
        if isinstance(value, str):
            if value.startswith(("http://", "https://")):
                return value
            return None

        if isinstance(value, dict):
            preferred_keys = [
                "redirectionUrl",
                "redirectionURL",
                "redirectUrl",
                "redirectURL",
                "checkoutUrl",
                "checkoutURL",
                "hostedPaymentPageUrl",
                "hostedPaymentPageURL",
                "paymentUrl",
                "paymentURL",
                "url",
                "href",
            ]

            for key in preferred_keys:
                found = self._find_any_url(value.get(key))
                if found:
                    return found

            links = value.get("links") or value.get("_links")
            found = self._find_any_url(links)
            if found:
                return found

            for nested_value in value.values():
                found = self._find_any_url(nested_value)
                if found:
                    return found

        if isinstance(value, list):
            for item in value:
                found = self._find_any_url(item)
                if found:
                    return found

        return None

    def build_connect_request(self, *, order: Any) -> dict[str, Any]:
        """
        Keep this method name so the rest of the backend does not need to know
        whether we use old TeleCash Connect or Fiserv Checkout Solution.
        """
        return self.build_checkout_request(order=order)

    def build_payment_link_request(self, *, order: Any) -> dict[str, Any]:
        """
        Backwards-compatible alias because order_service may still call the old method name.
        """
        return self.build_checkout_request(order=order)

    def build_checkout_request(self, *, order: Any) -> dict[str, Any]:
        if not all([self.base_url, self.api_key, self.api_secret, self.store_id]):
            return {
                "ok": False,
                "status_code": 500,
                "payload": {
                    "provider": "fiserv_checkout",
                    "error": "Missing Fiserv API-key configuration.",
                    "config_present": {
                        "base_url": bool(self.base_url),
                        "api_key": bool(self.api_key),
                        "api_secret": bool(self.api_secret),
                        "store_id": bool(self.store_id),
                    },
                },
                "redirect_url": None,
                "payment_link_id": None,
                "checkout_id": None,
                "action": None,
                "fields": {},
                "txndatetime": None,
            }

        endpoint = self._checkout_create_url()
        request_payload = self._build_checkout_payload(order=order)
        body_string = self._json_body(request_payload)
        headers = self._fiserv_headers(body_string)

        try:
            response = requests.post(
                endpoint,
                data=body_string.encode("utf-8"),
                headers=headers,
                timeout=30,
                verify=False,  # LOCAL SANDBOX ONLY. Remove for production.
            )

            try:
                response_body: Any = response.json()
            except ValueError:
                response_body = {"raw": response.text}

            redirect_url = self._find_checkout_redirect_url(response_body)
            checkout_id = self._find_checkout_id(response_body)

            print("========== FISERV CHECKOUT DEBUG ==========")
            print("Endpoint:", endpoint)
            print("Status:", response.status_code)
            print("Request:", json.dumps(request_payload, indent=2, ensure_ascii=False))
            print("Response:", json.dumps(response_body, indent=2, ensure_ascii=False))
            print("Redirect URL:", redirect_url)
            print("Checkout ID:", checkout_id)
            print("==========================================")

            ok = response.status_code in {200, 201} and bool(redirect_url)

            return {
                "ok": ok,
                "status_code": response.status_code,
                "payload": {
                    "provider": "fiserv_checkout",
                    "endpoint": endpoint,
                    "request": request_payload,
                    "response": response_body,
                    "headers": self.sanitize_headers(headers),
                    "diagnostic": {
                        "redirect_url_found": bool(redirect_url),
                        "checkout_id_found": bool(checkout_id),
                        "checkout_id": checkout_id,
                        "http_status": response.status_code,
                    },
                },
                "redirect_url": redirect_url,
                "payment_link_id": checkout_id,
                "checkout_id": checkout_id,
                "action": endpoint,
                "fields": {},
                "txndatetime": headers["Timestamp"],
            }

        except requests.RequestException as exc:
            print("========== FISERV CHECKOUT ERROR ==========")
            print("Endpoint:", endpoint)
            print("Error:", str(exc))
            print("==========================================")

            return {
                "ok": False,
                "status_code": 0,
                "payload": {
                    "provider": "fiserv_checkout",
                    "endpoint": endpoint,
                    "request": request_payload,
                    "error": str(exc),
                    "headers": self.sanitize_headers(headers),
                },
                "redirect_url": None,
                "payment_link_id": None,
                "checkout_id": None,
                "action": None,
                "fields": {},
                "txndatetime": None,
            }

    def verify_response_hash(self, payload: dict[str, Any], *, notification: bool = False) -> bool:
        """
        Checkout webhooks/returns are not verified here yet.

        For local sandbox testing this is intentionally permissive because:
        - localhost notification URLs cannot be called by Fiserv servers
        - the current frontend polling depends on our backend return route
        """
        return False

    def build_resume_html(self, *, action: str, fields: dict[str, Any]) -> str:
        """
        Legacy helper retained for compatibility with routes that may still call it.
        Checkout Solution should normally return redirect_url and not use this form.
        """
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
    def sanitize_headers(headers: dict[str, str]) -> dict[str, str]:
        hidden = {"Api-Key", "Message-Signature"}
        return {k: ("***" if k in hidden else str(v)) for k, v in headers.items()}
