from datetime import date
from pydantic import BaseModel, Field

from recipe import Recipe


class CookEvent(BaseModel):
    cooked_on: date
    notes: list[str] = Field(default_factory=list)


class CookbookRecipe(BaseModel):
    id: str | None = None
    recipe: Recipe
    favorite: bool = False

    rating: int | None = None
    notes: list[str] = Field(default_factory=list)

    cook_history: list[CookEvent] = Field(default_factory=list)


class Cookbook(BaseModel):
    id: str | None = None
    name: str
    recipes: list[CookbookRecipe] = Field(default_factory=list) 