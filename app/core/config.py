
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True)

    APP_NAME: str = "Sommerfrische Backend"
    DEBUG: bool = True
    API_V1_PREFIX: str = "/api/v1"
    DATABASE_URL: str = "sqlite:///./sommerfrische.db"
    BACKEND_CORS_ORIGINS: List[str] = ["http://localhost:5173", "http://localhost:3000"]

    TELECASH_BASE_URL: str = "https://prod.emea.api.fiservapps.com/sandbox"
    TELECASH_API_KEY: str = "gFv4FgnWo2AkWlmb85QumOzUiKXfcK1sV7FZ3VudHU1RNqTG"
    TELECASH_API_SECRET: str = "SLQGTHPQwhzPktELjrt9M6hyphW4mkgTn81MYZkfOVz9WKPdMasjJIVSqG4ekzgt"
    TELECASH_STORE_ID: str = "72305408"
    TELECASH_PAYMENT_LINK_EXPIRY_HOURS: int = 24

    TELECASH_SUCCESS_URL: str = "http://localhost:5173/payment/success"
    TELECASH_FAIL_URL: str = "http://localhost:5173/payment/failure"
    TELECASH_CANCEL_URL: str = "http://localhost:5173/payment/cancel"
    TELECASH_RETURN_BASE_URL: str = "http://localhost:8000/api/v1/payments/telecash/connect/return"
    TELECASH_NOTIFICATION_URL: str | None = None
    
    
    # Legacy Connect fallback, only used if API-key settings are missing
    TELECASH_CONNECT_URL: str = "https://www.ipg-online.com/connect/gateway/processing"
    TELECASH_STORE_NAME: str = "1251369401"
    TELECASH_SHARED_SECRET: str = "n*=g7pU5HkXF"
    TELECASH_TIMEZONE: str = "Europe/Berlin"
    TELECASH_PAYMENT_METHOD: str = ""
    TELECASH_LANGUAGE: str = "de_DE"
    TELECASH_CHECKOUT_OPTION: str = "combinedpage"
    TELECASH_CHECKOUT_MODE: str = ""
    TELECASH_BCOUNTRY: str = "AT"

    SENDGRID_API_KEY: str | None = "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"
    SENDGRID_FROM_EMAIL: str | None = "sommerfrische@wienenergie.at"
    SENDGRID_FROM_NAME: str = "Sommerfrische"
    PROVIDER_NOTIFICATION_EMAIL: str | None = "sommerfrische@wienenergie.at"
    PROVIDER_NOTIFICATION_NAME: str = "Logistik Sommerfrische"


settings = Settings()
