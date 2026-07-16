"""Platform-independent scratch boundary for parsing recipe-like text.

This module accepts text that has already been acquired from a description,
caption, or transcript. It does not fetch URLs, call an LLM, save recipes, or
depend on a particular social-media platform.

Planned tutorial stages:

1. Normalize the source text into meaningful lines.
2. Analyze every line for independent recipe-concept evidence.
3. Group nearby, compatible line evidence into recipe sections.
4. Build a review-only candidate from supported sections.
5. Report unclassified text and decide whether fallback extraction is needed.

Temporary working design
------------------------

The first analysis pass does not assign one final class to each line. It records
separate, non-exclusive strengths for concepts a line may belong to. For example,
an ``Ingredients`` line can strongly support both ``ingredient`` and ``heading``
without being an ingredient detail itself. ``ingredient`` means that the line
belongs with the ingredients part of a recipe. Ingredient-parser-nlp evidence
adjusts this existing strength; it does not create a separate ingredient-item
concept.

Concept strengths are rule weights, not probabilities, and do not need to add up
to one. Store them as numbers from ``0.0`` to ``1.0``; do not store categorical
values such as ``high`` or ``low``. Later grouping uses proximity and continuity:
ingredient-related lines
near an ingredient heading support one ingredients section; instruction-related
lines near each other support a steps section; adjacent narrative lines can form
a description.

For example, a future ``1. Chop the onion`` analysis might record
``ingredient: 0.1``, ``heading: 0.0``, and ``instruction: 0.9``. The exact
weights are future rule decisions, but the representation always uses numbers.

Blank lines retain their own structural evidence, such as ``blank`` and
``divider``. A blank run is stronger section-boundary evidence than one blank
line, but neither determines a boundary until the surrounding line evidence is
considered.

Ingredient-parser-nlp may provide ingredient-related evidence for each nonblank
line. Its result is supporting evidence only: extraction uses the already
recorded parser results for lines later selected as an ingredients section.
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


def normalize_lines(text: str) -> list[str]:
    """Return trimmed source lines without interpreting blank lines or content."""
    return [line.strip() for line in text.splitlines()]


def parse_recipe_text(text: str) -> RecipeTextParseResult:
    """Return a visible not-implemented result until parser rules are added."""

    normalized_lines = normalize_lines(text)
    return RecipeTextParseResult(
        unclassified_lines=normalized_lines,
        warnings=["Recipe text parsing is not implemented yet."],
        fallback_recommended=True,
    )


assert normalize_lines("") == []
assert normalize_lines("  \n\t\n") == ["", ""]
assert normalize_lines("  Pasta  \n\n  1 cup tomatoes  ") == [
    "Pasta",
    "",
    "1 cup tomatoes",
]
assert normalize_lines("• salt\r\n#weeknight\nMix  well") == [
    "• salt",
    "#weeknight",
    "Mix  well",
]
assert normalize_lines("Ingredients\n\nDirections") == [
    "Ingredients",
    "",
    "Directions",
]
