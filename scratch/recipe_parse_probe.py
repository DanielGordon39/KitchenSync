import argparse

from kitchensync.models import Recipe, RecipeIngredient
from kitchensync.parsing import parse_recipe


def recipe_to_markdown(recipe: Recipe) -> str:
    lines = [f"# {recipe.name}", ""]

    if recipe.metadata.description:
        lines.extend([recipe.metadata.description, ""])

    facts = []
    if recipe.servings is not None:
        facts.append(f"Servings: {recipe.servings}")
    if recipe.metadata.source_name:
        facts.append(f"Source: {recipe.metadata.source_name}")
    if recipe.metadata.source_url:
        facts.append(f"URL: {recipe.metadata.source_url}")

    if facts:
        lines.extend(f"- {fact}" for fact in facts)
        lines.append("")

    if recipe.ingredients:
        lines.extend(["## Ingredients", ""])
        lines.extend(f"- {_ingredient_to_markdown(ingredient)}" for ingredient in recipe.ingredients)
        lines.append("")

    if recipe.steps:
        lines.extend(["## Steps", ""])
        for step in recipe.steps:
            lines.extend([f"### Step {step.order}", ""])
            lines.extend(f"- {text}" for text in _step_bullets(step.text))
            lines.append("")

    return "\n".join(lines).strip() + "\n"


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
            pieces.append(str(ingredient.quantity.amount))
        if ingredient.quantity.unit:
            pieces.append(ingredient.quantity.unit)

    pieces.append(ingredient.ingredient.name)

    if ingredient.preparation:
        pieces.append(f"({ingredient.preparation})")

    return " ".join(pieces)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "url",
        nargs="?",
        default="https://www.hellofresh.com/recipes/blackened-chicken-penne-61b0d03ab3a03377ee6b1b04",
    )
    args = parser.parse_args()

    result = parse_recipe(args.url)

    print("status:", result.status.value)
    print("message:", result.message)

    if not result.recipe:
        return

    print()
    print(recipe_to_markdown(result.recipe))


if __name__ == "__main__":
    main()
