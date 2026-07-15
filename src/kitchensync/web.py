from fastapi import FastAPI
from pydantic import BaseModel

from .app import KitchenSyncApp


class CookbookCardDto(BaseModel):
    favorite: bool
    rating: int | None


class RecipeCardDto(BaseModel):
    recipe_id: str
    title: str
    image_url: str | None
    description: str | None
    cookbook: CookbookCardDto | None


app = FastAPI(title="KitchenSync")


@app.get("/api/recipes")
def list_recipes() -> list[RecipeCardDto]:
    with KitchenSyncApp.open() as kitchen_sync:
        recipes = kitchen_sync.recipes.list()

    return [
        RecipeCardDto(
            recipe_id=recipe["recipe_id"],
            title=recipe["title"],
            image_url=None,
            description=None,
            cookbook=None,
        )
        for recipe in recipes
    ]
