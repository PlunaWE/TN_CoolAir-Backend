import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, Text, String

from app.core.db import Base


class ContactSubmission(Base):
    __tablename__ = "contact_submissions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)
    email = Column(String, nullable=False)
    phone = Column(String, nullable=True)
    message = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
