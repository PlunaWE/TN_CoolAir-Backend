from pydantic import BaseModel

from app.schemas.common import ORMBase


class ContactIn(BaseModel):
    name: str
    email: str
    phone: str | None = None
    message: str


class ContactOut(ORMBase):
    id: str
    name: str
    email: str
    phone: str | None
    message: str
