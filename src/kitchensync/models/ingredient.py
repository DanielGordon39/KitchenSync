from __future__ import annotations

from typing import TypeAlias
from pydantic import BaseModel, Field


IngredientSlug: TypeAlias = str


class Ingredient(BaseModel):
    id: IngredientSlug | None = None
    name: str

    parent: Ingredient | None = None
    aliases: list[str] = Field(default_factory=list)

    preparation: str | None = None
    notes: list[str] = Field(default_factory=list)
