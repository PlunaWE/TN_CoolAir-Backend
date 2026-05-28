from sqlalchemy.orm import Session

from app.models.contact import ContactSubmission


class ContactService:
    def __init__(self, db: Session):
        self.db = db

    def submit(self, payload):
        entity = ContactSubmission(
            name=payload.name,
            email=payload.email,
            phone=payload.phone,
            message=payload.message,
        )
        self.db.add(entity)
        self.db.commit()
        self.db.refresh(entity)
        return entity
