from kitchensync.parsing import parse_recipe_ingredient_line


def test_parse_recipe_ingredient_line_extracts_preparation():
    ingredient = parse_recipe_ingredient_line("1 cup shredded lettuce")

    assert ingredient.ingredient.name == "lettuce"
    assert ingredient.quantity is not None
    assert ingredient.quantity.amount == 1
    assert ingredient.quantity.unit == "cup"
    assert ingredient.preparation == "shredded"
    assert ingredient.notes == ["raw: 1 cup shredded lettuce"]


def test_parse_recipe_ingredient_line_collapses_container_size():
    ingredient = parse_recipe_ingredient_line("2 28 ounce cans whole tomatoes")

    assert ingredient.ingredient.name == "canned whole tomatoes"
    assert ingredient.quantity is not None
    assert ingredient.quantity.amount == 56
    assert ingredient.quantity.unit == "ounce"
    assert ingredient.preparation is None
    assert ingredient.notes == ["raw: 2 28 ounce cans whole tomatoes"]


def test_parse_recipe_ingredient_line_moves_trailing_cut_form_to_preparation():
    ingredient = parse_recipe_ingredient_line("10 ounce Chicken Breast Strips")

    assert ingredient.ingredient.name == "Chicken Breast"
    assert ingredient.quantity is not None
    assert ingredient.quantity.amount == 10
    assert ingredient.quantity.unit == "ounce"
    assert ingredient.preparation == "Strips"
    assert ingredient.notes == ["raw: 10 ounce Chicken Breast Strips"]
