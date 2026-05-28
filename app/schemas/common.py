from decimal import Decimal
from pydantic import BaseModel, ConfigDict


class ORMBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class MoneyBase(BaseModel):
    total_amount: Decimal
