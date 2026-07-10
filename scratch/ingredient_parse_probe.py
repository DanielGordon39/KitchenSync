from kitchensync.models import Ingredient, RecipeIngredient

try:
    from ingredient_parser import parse_ingredient
    from kitchensync.parsing.ingredients import parse_recipe_ingredient_line
except ImportError as exc:
    raise SystemExit("Install ingredient-parser-nlp first: uv add ingredient-parser-nlp") from exc


def ingredient_to_string(ingredient: Ingredient) -> str:
    return ingredient.name


def recipe_ingredient_to_string(recipe_ingredient: RecipeIngredient) -> str:
    pieces = []

    if recipe_ingredient.quantity:
        if recipe_ingredient.quantity.amount is not None:
            pieces.append(_format_number(recipe_ingredient.quantity.amount))
        if recipe_ingredient.quantity.unit:
            pieces.append(recipe_ingredient.quantity.unit)

    if recipe_ingredient.preparation:
        pieces.append(recipe_ingredient.preparation)

    pieces.append(ingredient_to_string(recipe_ingredient.ingredient))

    return " ".join(pieces)


def _format_number(value: float) -> str:
    return str(int(value)) if float(value).is_integer() else str(value)


if __name__ == "__main__":
    examples = [
        "1 cup shredded lettuce",
        "2 28 ounce cans whole tomatoes",
        "1 Roma tomato, diced",
        "2 cloves garlic, minced",
    ]

    for text in examples:
        mapped = parse_recipe_ingredient_line(text)

        print(text)
        print("library:", parse_ingredient(text))
        print("display:", recipe_ingredient_to_string(mapped))
        print("model:", mapped)
        print()
