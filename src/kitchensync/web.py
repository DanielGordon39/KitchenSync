from typing import Annotated, Literal
from urllib.parse import quote

from fastapi import FastAPI, HTTPException, Query
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, field_validator

from .app import DEFAULT_DATABASE_PATH, KitchenSyncApp
from .markdown import slugify
from .models import Recipe, RecipeMetadata, RecipeStep, TimeEstimate
from .parsing.ingredients import parse_recipe_ingredient_line, project_ingredient_line


class CookbookCardDto(BaseModel):
    favorite: bool
    rating: int | None


class CookbookDetailDto(CookbookCardDto):
    notes: str | None


class RecipeCardDto(BaseModel):
    recipe_id: str
    title: str
    image_url: str | None
    description: str | None
    cookbook: CookbookCardDto | None
    tag_match: Literal["all", "some"] | None = None


class RecipeTagDto(BaseModel):
    tag_slug: str
    recipe_count: int


class IngredientCatalogItemDto(BaseModel):
    ingredient_id: str
    name: str
    slug: str | None
    aliases: list[str]
    default_unit: str | None


class IngredientLineParseRequest(BaseModel):
    lines: list[str] = Field(default_factory=list)


class IngredientLineProjectionDto(BaseModel):
    raw_text: str
    safe_for_rich: bool
    quantity_text: str | None
    unit: str | None
    ingredient_name: str | None
    preparation: str | None
    reason: str | None = None


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
    image_url: str | None
    tags: list[str]
    description: str | None
    notes: list[str]


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
    cookbook: CookbookDetailDto | None


class RecipeUpdateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str | None = None
    servings: int | None = Field(default=None, gt=0)
    time_estimate_minutes: int | None = Field(default=None, gt=0)
    tags: list[str] = Field(default_factory=list)
    ingredients: list[str] = Field(default_factory=list)
    steps: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)

    @field_validator("title")
    @classmethod
    def strip_title(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("title must not be blank")
        return value

    @field_validator("tags", "ingredients", "steps", "notes")
    @classmethod
    def strip_items(cls, values: list[str]) -> list[str]:
        return [value.strip() for value in values if value.strip()]


class CookbookUpdateRequest(BaseModel):
    favorite: bool = False
    rating: int | None = Field(default=None, ge=1, le=5)
    notes: str | None = None


app = FastAPI(title="KitchenSync")
app.mount(
    "/library",
    StaticFiles(directory=DEFAULT_DATABASE_PATH.parent, check_dir=False),
    name="library",
)


@app.get("/api/recipes")
def list_recipes(
    q: str = "",
    tag: Annotated[list[str] | None, Query()] = None,
    meal: Annotated[list[str] | None, Query()] = None,
    cuisine: Annotated[list[str] | None, Query()] = None,
    diet: Annotated[list[str] | None, Query()] = None,
    scope: Literal["global", "cookbook"] = "global",
) -> list[RecipeCardDto]:
    with KitchenSyncApp.open() as kitchen_sync:
        entries = {
            entry["recipe_id"]: entry for entry in kitchen_sync.cookbook.list_entries()
        }
        recipe_ids = set(entries) if scope == "cookbook" else None
        if q.strip() or tag or meal or cuisine or diet:
            recipes = kitchen_sync.recipes.search(
                q,
                exact_tags=tag,
                meal_tags=meal,
                cuisine_tags=cuisine,
                diet_tags=diet,
                recipe_ids=recipe_ids,
            )
        else:
            recipes = kitchen_sync.recipes.list(recipe_ids=recipe_ids)

    return [
        RecipeCardDto(
            recipe_id=recipe["recipe_id"],
            title=recipe["title"],
            image_url=_library_url(recipe.get("main_image_path")),
            description=None,
            cookbook=_cookbook_card(entries.get(recipe["recipe_id"])),
            tag_match=recipe.get("tag_match"),
        )
        for recipe in recipes
    ]


@app.get("/api/recipe-tags")
def list_recipe_tags(
    scope: Literal["global", "cookbook"] = "global",
) -> list[RecipeTagDto]:
    with KitchenSyncApp.open() as kitchen_sync:
        recipe_ids = None
        if scope == "cookbook":
            recipe_ids = {
                entry["recipe_id"] for entry in kitchen_sync.cookbook.list_entries()
            }
        tags = kitchen_sync.recipes.list_tags(recipe_ids=recipe_ids)

    return [RecipeTagDto.model_validate(tag) for tag in tags]


@app.get("/api/ingredients")
def list_ingredients() -> list[IngredientCatalogItemDto]:
    with KitchenSyncApp.open() as kitchen_sync:
        ingredients = kitchen_sync.ingredients.list()
    return [IngredientCatalogItemDto.model_validate(item) for item in ingredients]


@app.post("/api/ingredient-lines/parse")
def parse_ingredient_lines(
    request: IngredientLineParseRequest,
) -> list[IngredientLineProjectionDto]:
    return [
        IngredientLineProjectionDto.model_validate(project_ingredient_line(line))
        for line in request.lines
    ]


@app.get(
    "/api/recipes/{recipe_id}",
    responses={404: {"description": "Recipe not found"}},
)
def get_recipe_detail(recipe_id: str) -> RecipeDetailDto:
    with KitchenSyncApp.open() as kitchen_sync:
        detail = kitchen_sync.recipes.get_detail(recipe_id)
        entry = kitchen_sync.cookbook.get_entry(recipe_id)

    if detail is None:
        raise HTTPException(status_code=404, detail="Recipe not found")

    detail["recipe"]["image_url"] = _library_url(detail["recipe"].get("main_image_path"))
    detail["cookbook"] = _cookbook_detail(entry)
    return RecipeDetailDto.model_validate(detail)


@app.put(
    "/api/recipes/{recipe_id}",
    responses={404: {"description": "Recipe not found"}},
)
def update_recipe(recipe_id: str, request: RecipeUpdateRequest) -> RecipeDetailDto:
    with KitchenSyncApp.open() as kitchen_sync:
        existing = kitchen_sync.recipes.get_detail(recipe_id)
        if existing is None:
            raise HTTPException(status_code=404, detail="Recipe not found")

        existing_recipe = existing["recipe"]
        recipe = Recipe(
            name=request.title,
            servings=request.servings,
            ingredients=[
                parse_recipe_ingredient_line(line) for line in request.ingredients
            ],
            steps=[
                RecipeStep(order=index, text=text)
                for index, text in enumerate(request.steps, start=1)
            ],
            tags=list(
                dict.fromkeys(
                    slugify(tag.lstrip("#"))
                    for tag in request.tags
                    if tag.lstrip("#").strip()
                )
            ),
            time_estimate=(
                TimeEstimate(base_minutes=request.time_estimate_minutes)
                if request.time_estimate_minutes is not None
                else None
            ),
            notes=request.notes,
            metadata=RecipeMetadata(
                description=request.description.strip()
                if request.description and request.description.strip()
                else None,
                source_name=existing_recipe.get("source_name"),
                source_url=existing_recipe.get("source_url"),
                author=existing_recipe.get("author"),
                imported_from=existing_recipe.get("imported_from"),
            ),
        )
        detail = kitchen_sync.recipes.update_recipe(recipe_id, recipe)
        entry = kitchen_sync.cookbook.get_entry(recipe_id)
        if entry is not None:
            entry = kitchen_sync.cookbook.save_entry(
                recipe_id,
                favorite=bool(entry["favorite"]),
                rating=entry["rating"],
                notes=entry["notes"],
            )

    if detail is None:
        raise HTTPException(status_code=404, detail="Recipe not found")
    detail["recipe"]["image_url"] = _library_url(detail["recipe"].get("main_image_path"))
    detail["cookbook"] = _cookbook_detail(entry)
    return RecipeDetailDto.model_validate(detail)


@app.post(
    "/api/recipes/{recipe_id}/cookbook",
    responses={404: {"description": "Recipe not found"}},
)
def add_recipe_to_cookbook(recipe_id: str) -> CookbookDetailDto:
    with KitchenSyncApp.open() as kitchen_sync:
        entry = kitchen_sync.cookbook.get_entry(recipe_id)
        if entry is None:
            entry = kitchen_sync.cookbook.save_entry(recipe_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="Recipe not found")
    return CookbookDetailDto.model_validate(_cookbook_detail(entry))


@app.patch(
    "/api/recipes/{recipe_id}/cookbook",
    responses={404: {"description": "Cookbook entry not found"}},
)
def update_cookbook_entry(
    recipe_id: str,
    request: CookbookUpdateRequest,
) -> CookbookDetailDto:
    with KitchenSyncApp.open() as kitchen_sync:
        if kitchen_sync.cookbook.get_entry(recipe_id) is None:
            raise HTTPException(status_code=404, detail="Cookbook entry not found")
        entry = kitchen_sync.cookbook.save_entry(
            recipe_id,
            favorite=request.favorite,
            rating=request.rating,
            notes=request.notes.strip()
            if request.notes and request.notes.strip()
            else None,
        )
    return CookbookDetailDto.model_validate(_cookbook_detail(entry))


def _cookbook_card(entry: dict | None) -> CookbookCardDto | None:
    if entry is None:
        return None
    return CookbookCardDto(
        favorite=bool(entry["favorite"]),
        rating=entry["rating"],
    )


def _cookbook_detail(entry: dict | None) -> CookbookDetailDto | None:
    if entry is None:
        return None
    return CookbookDetailDto(
        favorite=bool(entry["favorite"]),
        rating=entry["rating"],
        notes=entry["notes"],
    )


def _library_url(path: str | None) -> str | None:
    if not path:
        return None

    return "/library/" + quote(path.replace("\\", "/"), safe="/")
