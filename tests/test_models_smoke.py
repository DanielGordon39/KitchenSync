from kitchensync.models import Cookbook, Ingredient, Recipe, RecipeIngredient


def test_core_models_import_and_construct():
    ingredient = Ingredient(name="salt")
    recipe_ingredient = RecipeIngredient(ingredient=ingredient, preparation="pinched")
    recipe = Recipe(name="Soup", ingredients=[recipe_ingredient])
    cookbook = Cookbook(name="Weeknights", recipes=[])

    assert ingredient.name == "salt"
    assert not hasattr(ingredient, "preparation")
    assert recipe.ingredients[0].preparation == "pinched"
    assert recipe.name == "Soup"
    assert cookbook.name == "Weeknights"
