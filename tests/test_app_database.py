import sqlite3
from uuid import UUID

import pytest

from kitchensync import KitchenSyncApp
from kitchensync.app import SCHEMA_SQL
from kitchensync.models import (
    ImageRef,
    Ingredient,
    Quantity,
    Recipe,
    RecipeIngredient,
    RecipeMetadata,
    RecipeStep,
    TimeEstimate,
)


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
        "recipe_tags",
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


def test_save_imported_recipe_writes_markdown_and_indexes_recipe_data(
    tmp_path,
    monkeypatch,
):
    import kitchensync.recipe_api as recipe_api

    monkeypatch.setattr(
        recipe_api,
        "_fetch_image",
        lambda uri: (b"fake image bytes", "image/jpeg"),
    )

    library_root = tmp_path / "library"
    recipe = Recipe(
        name="Tomato Soup",
        servings=4,
        tags=["soup", "weeknight"],
        time_estimate=TimeEstimate(base_minutes=45),
        metadata=RecipeMetadata(
            author="KitchenSync Test",
            imported_from="manual-test",
            images=[ImageRef(uri="https://example.com/tomato-soup.jpg")],
        ),
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
        tag_rows = app.connection.execute(
            """
            SELECT tag_order, tag_slug
            FROM recipe_tags
            WHERE recipe_id = ?
            ORDER BY tag_order
            """,
            (saved_recipe["recipe_id"],),
        ).fetchall()
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
        tag_search_results = app.recipes.search("weeknight")
        author_search_results = app.recipes.search("KitchenSync")
        step_search_results = app.recipes.search("Simmer")

    assert (library_root / "recipes" / "tomato-soup" / "recipe.md").exists()
    assert (
        library_root / "recipes" / "tomato-soup" / "images" / "main.jpg"
    ).read_bytes() == b"fake image bytes"
    assert (library_root / "ingredients" / "roma-tomato.md").exists()
    assert (library_root / "ingredients" / "chicken-stock.md").exists()

    assert saved_recipe["title"] == "Tomato Soup"
    assert saved_recipe["servings"] == 4
    assert saved_recipe["author"] == "KitchenSync Test"
    assert saved_recipe["imported_from"] == "manual-test"
    assert saved_recipe["time_estimate_minutes"] == 45
    assert saved_recipe["main_image_path"] == "recipes/tomato-soup/images/main.jpg"
    assert saved_recipe["markdown_path"] == "recipes/tomato-soup/recipe.md"
    assert "![Main recipe image](images/main.jpg)" in (
        library_root / "recipes" / "tomato-soup" / "recipe.md"
    ).read_text(encoding="utf-8")
    assert [dict(row) for row in tag_rows] == [
        {"tag_order": 1, "tag_slug": "soup"},
        {"tag_order": 2, "tag_slug": "weeknight"},
    ]
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
    assert [result["slug"] for result in tag_search_results] == ["tomato-soup"]
    assert [result["slug"] for result in author_search_results] == ["tomato-soup"]
    assert step_search_results == []


def test_recipe_and_ingredient_read_apis_return_ui_ready_rows(tmp_path):
    library_root = tmp_path / "library"
    recipe = Recipe(
        name="Tomato Soup",
        servings=4,
        tags=["soup", "weeknight"],
        time_estimate=TimeEstimate(base_minutes=45),
        metadata=RecipeMetadata(
            author="KitchenSync Test",
            imported_from="manual-test",
            source_url="https://example.com/tomato-soup",
        ),
        ingredients=[
            RecipeIngredient(
                ingredient=Ingredient(name="Roma Tomato"),
                quantity=Quantity(amount=6, unit="unit"),
                preparation="diced",
                notes=["raw: 6 Roma tomatoes, diced"],
            )
        ],
        steps=[RecipeStep(order=1, text="Simmer tomatoes.")],
    )

    with KitchenSyncApp.open(library_root / "kitchensync.sqlite") as app:
        app.recipes.save_imported_recipe(recipe)

        recipes = app.recipes.list()
        recipe_by_slug = app.recipes.get_by_slug("tomato-soup")
        detail = app.recipes.get_detail(recipes[0]["recipe_id"])
        ingredients = app.ingredients.list()
        missing_by_slug = app.recipes.get_by_slug("missing")
        missing_detail = app.recipes.get_detail("missing")

    assert len(recipes) == 1
    assert recipes[0]["title"] == "Tomato Soup"
    assert recipes[0]["tags"] == ["soup", "weeknight"]
    assert recipes[0]["time_estimate_minutes"] == 45
    assert recipe_by_slug is not None
    assert recipe_by_slug["recipe_id"] == recipes[0]["recipe_id"]
    assert detail == {
        "recipe": recipes[0],
        "ingredients": [
            {
                "ingredient_order": 1,
                "raw_text": "6 Roma tomatoes, diced",
                "ingredient_id": ingredients[0]["ingredient_id"],
                "parsed_name": "Roma Tomato",
                "quantity_amount": 6,
                "quantity_unit": "unit",
                "preparation": "diced",
            }
        ],
        "steps": [{"step_order": 1, "text": "Simmer tomatoes."}],
    }
    assert ingredients == [
        {
            "ingredient_id": ingredients[0]["ingredient_id"],
            "name": "Roma Tomato",
            "slug": "roma-tomato",
            "parent_ingredient_id": None,
            "category": None,
            "storage_area": None,
            "default_unit": None,
        }
    ]
    assert missing_by_slug is None
    assert missing_detail is None


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


def test_save_imported_recipe_uses_uuid_ids_and_reuses_by_source_url(tmp_path):
    library_root = tmp_path / "library"
    first_recipe = Recipe(
        name="Tomato Soup",
        metadata=RecipeMetadata(source_url="https://example.com/tomato-soup"),
        ingredients=[
            RecipeIngredient(
                ingredient=Ingredient(name="Roma Tomato"),
                notes=["raw: 6 Roma tomatoes"],
            )
        ],
    )
    updated_recipe = Recipe(
        name="Better Tomato Soup",
        metadata=RecipeMetadata(source_url="https://example.com/tomato-soup"),
        ingredients=[
            RecipeIngredient(
                ingredient=Ingredient(name="Roma Tomato"),
                notes=["raw: 8 Roma tomatoes"],
            )
        ],
    )

    with KitchenSyncApp.open(library_root / "kitchensync.sqlite") as app:
        app.recipes.save_imported_recipe(first_recipe)
        first_recipe_row = app.connection.execute(
            "SELECT recipe_id FROM recipe_recipes WHERE source_url = ?",
            ("https://example.com/tomato-soup",),
        ).fetchone()
        first_ingredient_row = app.connection.execute(
            "SELECT ingredient_id FROM ingredient_ingredients WHERE slug = ?",
            ("roma-tomato",),
        ).fetchone()

        app.recipes.save_imported_recipe(updated_recipe)
        recipe_rows = app.connection.execute(
            "SELECT recipe_id, title, slug FROM recipe_recipes"
        ).fetchall()
        ingredient_rows = app.connection.execute(
            "SELECT ingredient_id, slug FROM ingredient_ingredients"
        ).fetchall()
        ingredient_link = app.connection.execute(
            """
            SELECT ingredient_id
            FROM recipe_ingredients
            WHERE recipe_id = ?
            """,
            (first_recipe_row["recipe_id"],),
        ).fetchone()

    UUID(hex=first_recipe_row["recipe_id"])
    UUID(hex=first_ingredient_row["ingredient_id"])
    assert len(first_recipe_row["recipe_id"]) == 32
    assert len(first_ingredient_row["ingredient_id"]) == 32
    assert not first_recipe_row["recipe_id"].startswith("recipe_")
    assert not first_ingredient_row["ingredient_id"].startswith("ingredient_")
    assert [dict(row) for row in recipe_rows] == [
        {
            "recipe_id": first_recipe_row["recipe_id"],
            "title": "Better Tomato Soup",
            "slug": "better-tomato-soup",
        }
    ]
    assert [dict(row) for row in ingredient_rows] == [
        {
            "ingredient_id": first_ingredient_row["ingredient_id"],
            "slug": "roma-tomato",
        }
    ]
    assert ingredient_link["ingredient_id"] == first_ingredient_row["ingredient_id"]


def test_save_imported_recipe_reuses_existing_recipe_by_slug_without_source_url(
    tmp_path,
):
    library_root = tmp_path / "library"
    recipe = Recipe(name="Tomato Soup")

    with KitchenSyncApp.open(library_root / "kitchensync.sqlite") as app:
        app.recipes.save_imported_recipe(recipe)
        first_recipe_id = app.connection.execute(
            "SELECT recipe_id FROM recipe_recipes WHERE slug = ?",
            ("tomato-soup",),
        ).fetchone()["recipe_id"]

        app.recipes.save_imported_recipe(recipe)
        recipe_rows = app.connection.execute(
            "SELECT recipe_id FROM recipe_recipes WHERE slug = ?",
            ("tomato-soup",),
        ).fetchall()

    assert [row["recipe_id"] for row in recipe_rows] == [first_recipe_id]


def test_cookbook_entry_index_is_separate_from_recipe_existence(tmp_path):
    with KitchenSyncApp.open(tmp_path / "kitchensync.sqlite") as app:
        app.recipes.save_metadata(
            recipe_id="recipe_blackened_chicken_penne",
            title="Blackened Chicken Penne",
            slug="blackened-chicken-penne",
            markdown_path="recipes/blackened-chicken-penne/recipe.md",
        )

        assert app.cookbook.list_entries() == []

        app.cookbook.index_entry(
            recipe_id="recipe_blackened_chicken_penne",
            recipe_slug="blackened-chicken-penne",
            title="Blackened Chicken Penne",
            recipe_path="recipes/blackened-chicken-penne/recipe.md",
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
