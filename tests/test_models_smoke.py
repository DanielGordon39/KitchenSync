from kitchensync.models import (
    Cookbook,
    CookbookEntry,
    CookbookMetadata,
    Ingredient,
    Recipe,
    RecipeIngredient,
)


def test_core_models_import_and_construct():
    ingredient = Ingredient(name="salt")
    recipe_ingredient = RecipeIngredient(ingredient=ingredient, preparation="pinched")
    recipe = Recipe(name="Soup", ingredients=[recipe_ingredient])
    cookbook_entry = CookbookEntry(
        recipe=recipe,
        metadata=CookbookMetadata(favorite=True, rating=4),
    )
    cookbook = Cookbook(name="Weeknights", entries=[cookbook_entry])

    assert ingredient.name == "salt"
    assert not hasattr(ingredient, "preparation")
    assert recipe.ingredients[0].preparation == "pinched"
    assert recipe.name == "Soup"
    assert cookbook.name == "Weeknights"
    assert cookbook.entries[0].recipe.name == "Soup"
    assert cookbook.entries[0].metadata.favorite is True
