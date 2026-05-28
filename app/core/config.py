
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True)

    APP_NAME: str = "Sommerfrische Backend"
    DEBUG: bool = True
    API_V1_PREFIX: str = "/api/v1"
    DATABASE_URL: str = "sqlite:///./sommerfrische.db"
    BACKEND_CORS_ORIGINS: List[str] = ["http://localhost:5173", "http://localhost:3000"]

    TELECASH_CONNECT_URL: str = "https://www.ipg-online.com/connect/gateway/processing"
    TELECASH_STORE_NAME: str = "replace_me"
    TELECASH_SHARED_SECRET: str = "replace_me"
    TELECASH_TIMEZONE: str = "Europe/Berlin"
    TELECASH_SUCCESS_URL: str = "http://localhost:5173/payment/success"
    TELECASH_FAIL_URL: str = "http://localhost:5173/payment/failure"
    TELECASH_CANCEL_URL: str = "http://localhost:5173/payment/cancel"
    TELECASH_RETURN_BASE_URL: str = "http://localhost:8000/api/v1/payments/telecash/connect/return"
    TELECASH_NOTIFICATION_URL: str | None = None
    TELECASH_PAYMENT_METHOD: str = ""
    TELECASH_LANGUAGE: str = "de_DE"
    TELECASH_CHECKOUT_OPTION: str = "combinedpage"
    TELECASH_CHECKOUT_MODE: str = ""
    TELECASH_BCOUNTRY: str = "AT"

    SENDGRID_API_KEY: str | None = None
    SENDGRID_FROM_EMAIL: str | None = None
    SENDGRID_FROM_NAME: str = "Sommerfrische"
    PROVIDER_NOTIFICATION_EMAIL: str | None = None
    PROVIDER_NOTIFICATION_NAME: str = "Logistik Sommerfrische"


settings = Settings()
