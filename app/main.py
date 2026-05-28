from decimal import Decimal

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.core.config import settings
from app.core.db import Base, SessionLocal, engine
from app.models.product import Product

app = FastAPI(title=settings.APP_NAME)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(router, prefix=settings.API_V1_PREFIX)


@app.on_event("startup")
def startup():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        exists = db.query(Product).filter(Product.slug == "midea-portasplit-3-5kw").first()
        if not exists:
            db.add(Product(
                slug="midea-portasplit-3-5kw",
                name="Midea Portasplit 3,5 kW",
                subtitle="Kühlen + Wien Energie-Stromgutschein",
                description="Mobiles Split-Klimagerät mit optionalem Stromgutschein.",
                stock=50,
                room_size="bis 42 m²",
                energy_text="A++ Kühlen / A+ Heizen",
                noise_text="39 dB(A)",
                offer_stromvorteil_price=Decimal("949.00"),
                offer_solo_price=Decimal("849.00"),
            ))
            db.commit()
    finally:
        db.close()
