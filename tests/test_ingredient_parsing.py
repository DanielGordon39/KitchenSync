import pytest

from kitchensync.parsing import parse_recipe_ingredient_line, project_ingredient_line


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


def test_project_ingredient_line_preserves_editor_quantity_text():
    assert project_ingredient_line("1 1/2 cups flour") == {
        "raw_text": "1 1/2 cups flour",
        "safe_for_rich": True,
        "quantity_text": "1 1/2",
        "unit": "cup",
        "ingredient_name": "flour",
        "preparation": None,
        "reason": None,
    }
    assert project_ingredient_line("about 2-3 tablespoons chopped carrots") == {
        "raw_text": "about 2-3 tablespoons chopped carrots",
        "safe_for_rich": True,
        "quantity_text": "about 2-3",
        "unit": "tablespoon",
        "ingredient_name": "carrots",
        "preparation": "chopped",
        "reason": None,
    }


@pytest.mark.parametrize(
    ("line", "reason"),
    [
        ("salt to taste", "Comments such as 'to taste' need Raw view."),
        ("1 large onion, diced", "Size details need Raw view."),
        ("2 28 ounce cans whole tomatoes", "Multiple quantities need Raw view."),
    ],
)
def test_project_ingredient_line_keeps_complex_lines_raw(line, reason):
    projection = project_ingredient_line(line)

    assert projection["safe_for_rich"] is False
    assert projection["reason"] == reason
    assert projection["raw_text"] == line
