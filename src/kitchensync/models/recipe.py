from enum import StrEnum
from pydantic import BaseModel, Field

from common import Quantity
from ingredient import Ingredient
from tags import TagSlug


class ImageRef(BaseModel):
    uri: str
    alt_text: str | None = None
    caption: str | None = None


class RecipeMetadata(BaseModel):
    description: str | None = None
    source_name: str | None = None
    source_url: str | None = None
    author: str | None = None
    imported_from: str | None = None
    images: list[ImageRef] = Field(default_factory=list)


class RecipeIngredient(BaseModel):
    ingredient: Ingredient
    quantity: Quantity | None = None
    notes: list[str] = Field(default_factory=list)
    optional: bool = False


class RecipeStepType(StrEnum):
    PREP = "prep"
    COOK = "cook"
    REST = "rest"
    ASSEMBLE = "assemble"
    PLATE = "plate"
    SERVE = "serve"
    OTHER = "other"


class TimeEstimate(BaseModel):
    base_minutes: int | None = None
    serving_size_multiplier: float = 1.0


class RecipeStep(BaseModel):
    order: int
    text: str
    step_type: RecipeStepType | None = None
    ingredients: list[RecipeIngredient] = Field(default_factory=list)
    time_estimate: TimeEstimate | None = None
    images: list[ImageRef] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


class Recipe(BaseModel):
    id: str | None = None
    name: str
    servings: int | None = None
    
    ingredients: list[RecipeIngredient] = Field(default_factory=list)
    steps: list[RecipeStep] = Field(default_factory=list)
    
    tags: list[TagSlug] = Field(default_factory=list)
    time_estimate: TimeEstimate | None = None
    notes: list[str] = Field(default_factory=list)
    metadata: RecipeMetadata = Field(default_factory=RecipeMetadata)