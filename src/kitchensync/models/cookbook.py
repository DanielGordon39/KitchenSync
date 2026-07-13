from datetime import date

from pydantic import BaseModel, Field

from .recipe import Recipe


class CookEvent(BaseModel):
    cooked_on: date
    notes: list[str] = Field(default_factory=list)


class CookbookMetadata(BaseModel):
    favorite: bool = False
    rating: int | None = None
    status: str = "active"
    notes: list[str] = Field(default_factory=list)
    cook_history: list[CookEvent] = Field(default_factory=list)


class CookbookEntry(BaseModel):
    recipe: Recipe
    metadata: CookbookMetadata = Field(default_factory=CookbookMetadata)


class Cookbook(BaseModel):
    id: str | None = None
    name: str
    entries: list[CookbookEntry] = Field(default_factory=list)
