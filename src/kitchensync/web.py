from fastapi import FastAPI, HTTPException
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


class RecipeDetailRecipeDto(BaseModel):
    recipe_id: str
    title: str
    slug: str | None
    servings: int | None
    source_name: str | None
    source_url: str | None
    author: str | None
    imported_from: str | None
    time_estimate_minutes: int | None
    tags: list[str]


class RecipeIngredientDto(BaseModel):
    ingredient_order: int
    raw_text: str
    ingredient_id: str | None
    parsed_name: str | None
    quantity_amount: float | None
    quantity_unit: str | None
    preparation: str | None


class RecipeStepDto(BaseModel):
    step_order: int
    text: str


class RecipeDetailDto(BaseModel):
    recipe: RecipeDetailRecipeDto
    ingredients: list[RecipeIngredientDto]
    steps: list[RecipeStepDto]


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


@app.get(
    "/api/recipes/{recipe_id}",
    responses={404: {"description": "Recipe not found"}},
)
def get_recipe_detail(recipe_id: str) -> RecipeDetailDto:
    with KitchenSyncApp.open() as kitchen_sync:
        detail = kitchen_sync.recipes.get_detail(recipe_id)

    if detail is None:
        raise HTTPException(status_code=404, detail="Recipe not found")

    return RecipeDetailDto.model_validate(detail)
