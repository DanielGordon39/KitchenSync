from pydantic import BaseModel
from typing import TypeAlias



UnitSlug: TypeAlias = str


class Quantity(BaseModel):
    amount: float | None = None
    # TODO implement custom Unit class
    unit: UnitSlug | None = None
