# Sommerfrische Backend

FastAPI backend for the Sommerfrische webshop.

## Run
```powershell
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
uvicorn app.main:app --reload --reload-exclude ".venv/*"
```

The app seeds one product with two offers:
- `stromvorteil` → 949 EUR
- `solo` → 849 EUR

## Notes
- Payment uses a TeleCash payment-link flow.
- Successful payment triggers stock reduction.
- Customer confirmation email and provider notification email are sent via SendGrid when configured.
- Image assets are handled by the frontend only.
