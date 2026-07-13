import sqlite3

import pytest

from kitchensync import KitchenSyncApp
from kitchensync.app import SCHEMA_SQL
from kitchensync.models import Ingredient, Quantity, Recipe, RecipeIngredient, RecipeStep


def test_open_initializes_v1_database_tables(tmp_path):
    database_path = tmp_path / "kitchensync.sqlite"

    with KitchenSyncApp.open(database_path) as app:
        table_names = {
            row["name"]
            for row in app.connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }

    assert {
        "recipe_recipes",
        "recipe_ingredients",
        "recipe_steps",
        "recipe_search",
        "ingredient_ingredients",
        "ingredient_aliases",
        "ingredient_packaging",
        "ingredient_conversions",
        "cookbook_entries",
        "cookbook_cook_events",
        "pantry_items",
        "shopping_lists",
        "shopping_items",
        "candidate_candidates",
        "candidate_events",
    } <= table_names
    assert database_path.exists()


def test_recipe_metadata_can_be_saved_retrieved_and_searched(tmp_path):
    with KitchenSyncApp.open(tmp_path / "kitchensync.sqlite") as app:
        app.recipes.save_metadata(
            recipe_id="recipe_blackened_chicken_penne",
            title="Blackened Chicken Penne",
            slug="blackened-chicken-penne",
            servings=2,
            source_name="HelloFresh",
            source_url="https://example.com/blackened-chicken-penne",
        )

        recipe = app.recipes.get("recipe_blackened_chicken_penne")
        results = app.recipes.search("chicken")

    assert recipe is not None
    assert recipe["title"] == "Blackened Chicken Penne"
    assert recipe["servings"] == 2
    assert [result["recipe_id"] for result in results] == [
        "recipe_blackened_chicken_penne"
    ]


def test_recipe_metadata_upsert_updates_search_text(tmp_path):
    with KitchenSyncApp.open(tmp_path / "kitchensync.sqlite") as app:
        app.recipes.save_metadata(
            recipe_id="recipe_soup",
            title="Tomato Soup",
            slug="tomato-soup",
        )
        app.recipes.save_metadata(
            recipe_id="recipe_soup",
            title="Roasted Pepper Soup",
            slug="roasted-pepper-soup",
        )

        assert app.recipes.search("tomato") == []
        results = app.recipes.search("pepper")

    assert len(results) == 1
    assert results[0]["title"] == "Roasted Pepper Soup"


def test_save_imported_recipe_writes_markdown_and_indexes_recipe_data(tmp_path):
    library_root = tmp_path / "library"
    recipe = Recipe(
        name="Tomato Soup",
        servings=4,
        ingredients=[
            RecipeIngredient(
                ingredient=Ingredient(name="Roma Tomato"),
                quantity=Quantity(amount=6, unit="unit"),
                preparation="diced",
                notes=["raw: 6 Roma tomatoes, diced"],
            ),
            RecipeIngredient(
                ingredient=Ingredient(name="Chicken Stock"),
                quantity=Quantity(amount=2, unit="cup"),
                notes=["raw: 2 cups chicken stock"],
            ),
        ],
        steps=[
            RecipeStep(order=1, text="Dice tomatoes."),
            RecipeStep(order=2, text="Simmer tomatoes with chicken stock."),
        ],
    )

    with KitchenSyncApp.open(library_root / "kitchensync.sqlite") as app:
        app.recipes.save_imported_recipe(recipe)

        saved_recipe = app.connection.execute(
            "SELECT * FROM recipe_recipes WHERE slug = ?",
            ("tomato-soup",),
        ).fetchone()
        ingredient_rows = app.connection.execute(
            """
            SELECT ingredient_order, raw_text, parsed_name, quantity_amount,
                   quantity_unit, preparation
            FROM recipe_ingredients
            WHERE recipe_id = ?
            ORDER BY ingredient_order
            """,
            (saved_recipe["recipe_id"],),
        ).fetchall()
        step_rows = app.connection.execute(
            """
            SELECT step_order, text
            FROM recipe_steps
            WHERE recipe_id = ?
            ORDER BY step_order
            """,
            (saved_recipe["recipe_id"],),
        ).fetchall()
        ingredient_catalog_rows = app.connection.execute(
            """
            SELECT slug, name
            FROM ingredient_ingredients
            ORDER BY slug
            """
        ).fetchall()
        search_results = app.recipes.search("stock")

    assert (library_root / "recipes" / "tomato-soup.md").exists()
    assert (library_root / "ingredients" / "roma-tomato.md").exists()
    assert (library_root / "ingredients" / "chicken-stock.md").exists()

    assert saved_recipe["title"] == "Tomato Soup"
    assert saved_recipe["servings"] == 4
    assert saved_recipe["markdown_path"] == "recipes/tomato-soup.md"
    assert [dict(row) for row in ingredient_rows] == [
        {
            "ingredient_order": 1,
            "raw_text": "6 Roma tomatoes, diced",
            "parsed_name": "Roma Tomato",
            "quantity_amount": 6,
            "quantity_unit": "unit",
            "preparation": "diced",
        },
        {
            "ingredient_order": 2,
            "raw_text": "2 cups chicken stock",
            "parsed_name": "Chicken Stock",
            "quantity_amount": 2,
            "quantity_unit": "cup",
            "preparation": None,
        },
    ]
    assert [dict(row) for row in step_rows] == [
        {"step_order": 1, "text": "Dice tomatoes."},
        {"step_order": 2, "text": "Simmer tomatoes with chicken stock."},
    ]
    assert [dict(row) for row in ingredient_catalog_rows] == [
        {"slug": "chicken-stock", "name": "Chicken Stock"},
        {"slug": "roma-tomato", "name": "Roma Tomato"},
    ]
    assert [result["slug"] for result in search_results] == ["tomato-soup"]


def test_save_imported_recipe_does_not_overwrite_existing_ingredient_markdown(
    tmp_path,
):
    library_root = tmp_path / "library"
    ingredient_path = library_root / "ingredients" / "roma-tomato.md"
    existing_ingredient_markdown = """# Roma Tomato

## Aliases

```yaml
- plum tomato
```

## Notes

- Keep this hand-written note.
"""
    ingredient_path.parent.mkdir(parents=True)
    ingredient_path.write_text(existing_ingredient_markdown, encoding="utf-8")

    recipe = Recipe(
        name="Tomato Soup",
        ingredients=[
            RecipeIngredient(
                ingredient=Ingredient(name="Roma Tomato"),
                notes=["raw: 6 Roma tomatoes"],
            )
        ],
    )

    with KitchenSyncApp.open(library_root / "kitchensync.sqlite") as app:
        app.recipes.save_imported_recipe(recipe)
        ingredient = app.connection.execute(
            "SELECT * FROM ingredient_ingredients WHERE slug = ?",
            ("roma-tomato",),
        ).fetchone()

    assert ingredient["name"] == "Roma Tomato"
    assert ingredient_path.read_text(encoding="utf-8") == existing_ingredient_markdown


def test_cookbook_entry_index_is_separate_from_recipe_existence(tmp_path):
    with KitchenSyncApp.open(tmp_path / "kitchensync.sqlite") as app:
        app.recipes.save_metadata(
            recipe_id="recipe_blackened_chicken_penne",
            title="Blackened Chicken Penne",
            slug="blackened-chicken-penne",
            markdown_path="recipes/blackened-chicken-penne.md",
        )

        assert app.cookbook.list_entries() == []

        app.cookbook.index_entry(
            recipe_id="recipe_blackened_chicken_penne",
            recipe_slug="blackened-chicken-penne",
            title="Blackened Chicken Penne",
            recipe_path="recipes/blackened-chicken-penne.md",
            cookbook_path="cookbook/blackened-chicken-penne.md",
            favorite=True,
            rating=4,
        )
        cookbook_entries = app.cookbook.list_entries()

    assert len(cookbook_entries) == 1
    assert cookbook_entries[0]["recipe_id"] == "recipe_blackened_chicken_penne"
    assert cookbook_entries[0]["recipe_slug"] == "blackened-chicken-penne"
    assert cookbook_entries[0]["cookbook_path"] == "cookbook/blackened-chicken-penne.md"
    assert cookbook_entries[0]["favorite"] == 1
    assert cookbook_entries[0]["rating"] == 4


def test_cookbook_entry_cannot_reference_missing_recipe(tmp_path):
    with KitchenSyncApp.open(tmp_path / "kitchensync.sqlite") as app:
        with pytest.raises(sqlite3.IntegrityError):
            app.cookbook.index_entry(
                recipe_id="missing_recipe",
                title="Missing Recipe",
                cookbook_path="cookbook/missing-recipe.md",
            )


def test_cookbook_entry_rating_must_be_one_to_five(tmp_path):
    with KitchenSyncApp.open(tmp_path / "kitchensync.sqlite") as app:
        app.recipes.save_metadata(recipe_id="recipe_soup", title="Soup")

        with pytest.raises(ValueError, match="rating"):
            app.cookbook.index_entry(
                recipe_id="recipe_soup",
                title="Soup",
                cookbook_path="cookbook/soup.md",
                rating=6,
            )


def test_schema_sql_uses_one_physical_database_with_logical_prefixes():
    assert "ATTACH DATABASE" not in SCHEMA_SQL
    assert "recipe_recipes" in SCHEMA_SQL
    assert "ingredient_ingredients" in SCHEMA_SQL
    assert "cookbook_entries" in SCHEMA_SQL
    assert "pantry_items" in SCHEMA_SQL
    assert "shopping_lists" in SCHEMA_SQL
    assert "candidate_candidates" in SCHEMA_SQL
