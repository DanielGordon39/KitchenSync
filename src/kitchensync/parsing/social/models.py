"""Intermediate models for deterministic social-recipe parsing."""

from pydantic import BaseModel, Field


class SocialRecipeCandidate(BaseModel):
    """Incomplete recipe details extracted for review, never direct saving."""

    name: str | None = None
    description: str | None = None
    servings: int | None = None
    raw_ingredients: list[str] = Field(default_factory=list)
    steps: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


class LineAnalysis(BaseModel):
    """Independent recipe-concept evidence for one normalized source line."""

    line_number: int
    text: str
    evidence: dict[str, float] = Field(default_factory=dict)


class RecipeFieldCandidate(BaseModel):
    """Possible Recipe fields associated with one contextual run of lines."""

    field_scores: dict[str, float]
    line_numbers: list[int]
    lines: list[str]


class RecipeTextParseResult(BaseModel):
    """Candidate plus diagnostics from deterministic text parsing."""

    candidate: SocialRecipeCandidate | None = None
    line_analyses: list[LineAnalysis] = Field(default_factory=list)
    field_candidates: list[RecipeFieldCandidate] = Field(default_factory=list)
    unclassified_lines: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    fallback_recommended: bool = False
