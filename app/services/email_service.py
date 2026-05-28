from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

from app.core.config import settings


class EmailService:
    def __init__(self) -> None:
        self.api_key = settings.SENDGRID_API_KEY
        self.from_email = settings.SENDGRID_FROM_EMAIL
        self.from_name = settings.SENDGRID_FROM_NAME
        self.provider_email = settings.PROVIDER_NOTIFICATION_EMAIL
        self.provider_name = settings.PROVIDER_NOTIFICATION_NAME

    def is_enabled(self) -> bool:
        return bool(self.api_key and self.from_email)

    def send_order_confirmation(
        self,
        *,
        to_email: str,
        customer_name: str,
        order_id: str,
        total_amount: str,
        currency: str,
    ) -> None:
        if not self.is_enabled():
            return

        subject = "Deine Bestellung bei Sommerfrische"
        html_content = f"""
        <html><body style="font-family: Arial, sans-serif; color: #1f2937;">
        <h2>Vielen Dank für deine Bestellung!</h2>
        <p>Hallo {customer_name},</p>
        <p>deine Zahlung wurde erfolgreich bestätigt.</p>
        <p><strong>Bestellnummer:</strong> {order_id}</p>
        <p><strong>Gesamtbetrag:</strong> {currency} {total_amount}</p>
        <p>Viele Grüße<br/>Sommerfrische</p>
        </body></html>
        """
        message = Mail(
            from_email=(self.from_email, self.from_name),
            to_emails=to_email,
            subject=subject,
            html_content=html_content,
        )
        try:
            SendGridAPIClient(self.api_key).send(message)
        except Exception as exc:
            print("SendGrid customer email failed:", repr(exc))

    def send_provider_notification(
        self,
        *,
        order_id: str,
        customer_name: str,
        customer_email: str,
        customer_phone: str | None,
        shipping_name: str,
        shipping_line1: str,
        shipping_line2: str | None,
        shipping_city: str,
        shipping_postal_code: str,
        shipping_country: str,
        total_amount: str,
        currency: str,
        notes: str | None,
        items: list[dict],
    ) -> None:
        if not self.is_enabled() or not self.provider_email:
            return

        subject = f"Neue bezahlte Bestellung: {order_id}"
        items_html = "".join(
            f"<li>{item['offer_name']} x {item['quantity']} ({item['line_total']} {currency})</li>"
            for item in items
        )
        shipping_line2_html = f"{shipping_line2}<br/>" if shipping_line2 else ""

        html_content = f"""
        <html><body style="font-family: Arial, sans-serif; color: #1f2937;">
        <h2>Neue bezahlte Bestellung</h2>
        <p><strong>Bestellnummer:</strong> {order_id}</p>
        <p><strong>Gesamtbetrag:</strong> {currency} {total_amount}</p>
        <h3>Kundendaten</h3>
        <p><strong>Name:</strong> {customer_name}</p>
        <p><strong>E-Mail:</strong> {customer_email}</p>
        <p><strong>Telefon:</strong> {customer_phone or "-"}</p>
        <h3>Lieferadresse</h3>
        <p>{shipping_name}<br/>{shipping_line1}<br/>{shipping_line2_html}{shipping_postal_code} {shipping_city}<br/>{shipping_country}</p>
        <h3>Bestellte Artikel</h3>
        <ul>{items_html}</ul>
        <h3>Notiz</h3>
        <p>{notes or "-"}</p>
        </body></html>
        """
        message = Mail(
            from_email=(self.from_email, self.from_name),
            to_emails=(self.provider_email, self.provider_name),
            subject=subject,
            html_content=html_content,
        )
        try:
            SendGridAPIClient(self.api_key).send(message)
        except Exception as exc:
            print("SendGrid provider email failed:", repr(exc))
