from __future__ import annotations

import re
from pathlib import Path

from .models import Ingredient, Recipe, RecipeIngredient

__all__ = [
    "ingredient_to_markdown",
    "raw_ingredient_text",
    "recipe_to_markdown",
    "slugify",
    "write_recipe_markdown_files",
]


def recipe_to_markdown(recipe: Recipe, *, main_image_path: str | None = None) -> str:
    lines = [f"# {recipe.name}", ""]

    if recipe.metadata.description:
        lines.extend([recipe.metadata.description, ""])

    facts = _recipe_facts(recipe)
    if facts:
        lines.extend(f"- {fact}" for fact in facts)
        lines.append("")

    if main_image_path:
        lines.extend(["## Images", "", f"![Main recipe image]({main_image_path})", ""])

    if recipe.ingredients:
        lines.extend(["## Ingredients", ""])
        lines.extend(
            f"- {raw_ingredient_text(ingredient)}"
            for ingredient in recipe.ingredients
        )
        lines.append("")

    if recipe.steps:
        lines.extend(["## Steps", ""])
        for step in recipe.steps:
            lines.extend([f"### Step {step.order}", ""])
            lines.extend(f"- {text}" for text in _step_bullets(step.text))
            lines.append("")

    if recipe.notes:
        lines.extend(["## Notes", ""])
        lines.extend(f"- {note}" for note in recipe.notes)
        lines.append("")

    return "\n".join(lines).strip() + "\n"


def ingredient_to_markdown(ingredient: Ingredient) -> str:
    aliases = ingredient.aliases or [ingredient.name.casefold()]
    lines = [
        f"# {ingredient.name}",
        "",
        "## Aliases",
        "",
        "```yaml",
        *(f"- {alias}" for alias in aliases),
        "```",
    ]

    if ingredient.notes:
        lines.extend(["", "## Notes", ""])
        lines.extend(f"- {note}" for note in ingredient.notes)

    return "\n".join(lines).strip() + "\n"


def write_recipe_markdown_files(recipe: Recipe, output_dir: Path) -> list[Path]:
    recipe_dir = output_dir / "recipes"
    ingredient_dir = output_dir / "ingredients"
    recipe_dir.mkdir(parents=True, exist_ok=True)
    ingredient_dir.mkdir(parents=True, exist_ok=True)

    paths = []
    recipe_path = recipe_dir / slugify(recipe.name) / "recipe.md"
    recipe_path.parent.mkdir(parents=True, exist_ok=True)
    recipe_path.write_text(recipe_to_markdown(recipe), encoding="utf-8")
    paths.append(recipe_path)

    for ingredient_name in dict.fromkeys(
        recipe_ingredient.ingredient.name for recipe_ingredient in recipe.ingredients
    ):
        ingredient = Ingredient(name=ingredient_name)
        ingredient_path = ingredient_dir / f"{slugify(ingredient.name)}.md"
        ingredient_path.write_text(
            ingredient_to_markdown(ingredient),
            encoding="utf-8",
        )
        paths.append(ingredient_path)

    return paths


def raw_ingredient_text(ingredient: RecipeIngredient) -> str:
    raw_prefix = "raw: "
    for note in ingredient.notes:
        if note.startswith(raw_prefix):
            return note.removeprefix(raw_prefix)

    return _ingredient_to_markdown(ingredient)


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.casefold()).strip("-")
    return slug or "untitled"


def _recipe_facts(recipe: Recipe) -> list[str]:
    facts = []
    if recipe.servings is not None:
        facts.append(f"Servings: {recipe.servings}")
    if recipe.time_estimate and recipe.time_estimate.base_minutes is not None:
        facts.append(f"Time: {recipe.time_estimate.base_minutes} minutes")
    if recipe.tags:
        facts.append(f"Tags: {', '.join(recipe.tags)}")
    if recipe.metadata.source_name:
        facts.append(f"Source: {recipe.metadata.source_name}")
    if recipe.metadata.author:
        facts.append(f"Author: {recipe.metadata.author}")
    if recipe.metadata.source_url:
        facts.append(f"URL: {recipe.metadata.source_url}")
    if recipe.metadata.imported_from:
        facts.append(f"Imported from: {recipe.metadata.imported_from}")
    return facts


def _step_bullets(text: str) -> list[str]:
    bullets = [part.strip() for part in text.split("•") if part.strip()]
    if bullets:
        return bullets

    text = text.strip()
    if text:
        return [text]

    return []


def _ingredient_to_markdown(ingredient: RecipeIngredient) -> str:
    pieces = []
    if ingredient.quantity:
        if ingredient.quantity.amount is not None:
            pieces.append(_format_number(ingredient.quantity.amount))
        if ingredient.quantity.unit:
            pieces.append(ingredient.quantity.unit)

    pieces.append(ingredient.ingredient.name)

    if ingredient.preparation:
        pieces.append(f"({ingredient.preparation})")

    return " ".join(pieces)


def _format_number(value: float) -> str:
    return str(int(value)) if float(value).is_integer() else str(value)
