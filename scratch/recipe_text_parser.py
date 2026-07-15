"""Platform-independent scratch boundary for parsing recipe-like text.

This module accepts text that has already been acquired from a description,
caption, or transcript. It does not fetch URLs, call an LLM, save recipes, or
depend on a particular social-media platform.

Planned tutorial stages:

1. Normalize the source text into meaningful lines.
2. Classify lines without creator-specific rules.
3. Group classified lines into recipe sections.
4. Build a review-only candidate from supported sections.
5. Report unclassified text and decide whether fallback extraction is needed.
"""

from pydantic import BaseModel, Field


class SocialRecipeCandidate(BaseModel):
    """Incomplete recipe details extracted for review, never direct saving."""

    name: str | None = None
    servings: int | None = None
    raw_ingredients: list[str] = Field(default_factory=list)
    steps: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


class RecipeTextParseResult(BaseModel):
    """Candidate plus diagnostics from deterministic text parsing."""

    candidate: SocialRecipeCandidate | None = None
    unclassified_lines: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    fallback_recommended: bool = False


def parse_recipe_text(text: str) -> RecipeTextParseResult:
    """Return a visible not-implemented result until parser rules are added."""

    nonblank_lines = [line.strip() for line in text.splitlines() if line.strip()]
    return RecipeTextParseResult(
        unclassified_lines=nonblank_lines,
        warnings=["Recipe text parsing is not implemented yet."],
        fallback_recommended=True,
    )
