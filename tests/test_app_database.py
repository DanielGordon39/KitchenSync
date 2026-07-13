import sqlite3

import pytest

from kitchensync import KitchenSyncApp
from kitchensync.app import SCHEMA_SQL


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
