import pytest
from fastapi import HTTPException

from kitchensync import KitchenSyncApp
from kitchensync import web
from kitchensync.models import Ingredient, Recipe, RecipeIngredient, RecipeStep


class FakeCookbookAPI:
    def list_entries(self):
        return []

    def get_entry(self, recipe_id):
        return None


def test_list_recipes_delegates_and_shapes_recipe_cards(monkeypatch):
    class FakeRecipesAPI:
        def list(self, recipe_ids=None):
            return [
                {
                    "recipe_id": "recipe_tomato_soup",
                    "title": "Tomato Soup",
                    "main_image_path": "recipes/tomato-soup/images/main.jpg",
                    "ignored_index_field": "not exposed",
                }
            ]

    class FakeKitchenSync:
        def __init__(self):
            self.recipes = FakeRecipesAPI()
            self.cookbook = FakeCookbookAPI()
            self.closed = False

        def __enter__(self):
            return self

        def __exit__(self, *exc_info):
            self.closed = True

    fake_kitchen_sync = FakeKitchenSync()

    class FakeKitchenSyncApp:
        @staticmethod
        def open():
            return fake_kitchen_sync

    monkeypatch.setattr(web, "KitchenSyncApp", FakeKitchenSyncApp)

    recipes = web.list_recipes()

    assert [recipe.model_dump() for recipe in recipes] == [
        {
            "recipe_id": "recipe_tomato_soup",
            "title": "Tomato Soup",
            "image_url": "/library/recipes/tomato-soup/images/main.jpg",
            "description": None,
            "cookbook": None,
            "tag_match": None,
        }
    ]
    assert fake_kitchen_sync.closed is True


def test_list_recipes_delegates_search_and_filter_parameters(monkeypatch):
    class FakeRecipesAPI:
        def __init__(self):
            self.search_arguments = None

        def search(self, query, **filters):
            self.search_arguments = (query, filters)
            return [
                {
                    "recipe_id": "recipe_tomato_soup",
                    "title": "Tomato Soup",
                    "main_image_path": None,
                    "tag_match": "some",
                }
            ]

    fake_recipes = FakeRecipesAPI()

    class FakeKitchenSync:
        def __init__(self):
            self.recipes = fake_recipes
            self.cookbook = FakeCookbookAPI()

        def __enter__(self):
            return self

        def __exit__(self, *exc_info):
            return None

    class FakeKitchenSyncApp:
        @staticmethod
        def open():
            return FakeKitchenSync()

    monkeypatch.setattr(web, "KitchenSyncApp", FakeKitchenSyncApp)

    recipes = web.list_recipes(
        q="chicken",
        tag=["quick-and-easy", "dinner"],
        meal=["lunch"],
        cuisine=["korean"],
        diet=["low-carb"],
    )

    assert fake_recipes.search_arguments == (
        "chicken",
        {
            "exact_tags": ["quick-and-easy", "dinner"],
            "meal_tags": ["lunch"],
            "cuisine_tags": ["korean"],
            "diet_tags": ["low-carb"],
            "recipe_ids": None,
        },
    )
    assert recipes[0].tag_match == "some"


def test_list_recipe_tags_delegates_and_shapes_counts(monkeypatch):
    class FakeRecipesAPI:
        def list_tags(self, recipe_ids=None):
            return [{"tag_slug": "weeknight", "recipe_count": 4}]

    class FakeKitchenSync:
        def __init__(self):
            self.recipes = FakeRecipesAPI()
            self.cookbook = FakeCookbookAPI()

        def __enter__(self):
            return self

        def __exit__(self, *exc_info):
            return None

    class FakeKitchenSyncApp:
        @staticmethod
        def open():
            return FakeKitchenSync()

    monkeypatch.setattr(web, "KitchenSyncApp", FakeKitchenSyncApp)

    tags = web.list_recipe_tags()

    assert [tag.model_dump() for tag in tags] == [
        {"tag_slug": "weeknight", "recipe_count": 4}
    ]


def test_list_ingredients_exposes_editor_catalog(monkeypatch):
    class FakeIngredientsAPI:
        def list(self):
            return [
                {
                    "ingredient_id": "ingredient_scallion",
                    "name": "Scallion",
                    "slug": "scallion",
                    "aliases": ["green onion"],
                    "default_unit": "bunch",
                    "category": "produce",
                    "storage_area": "fridge",
                }
            ]

    class FakeKitchenSync:
        def __init__(self):
            self.ingredients = FakeIngredientsAPI()

        def __enter__(self):
            return self

        def __exit__(self, *exc_info):
            return None

    class FakeKitchenSyncApp:
        @staticmethod
        def open():
            return FakeKitchenSync()

    monkeypatch.setattr(web, "KitchenSyncApp", FakeKitchenSyncApp)

    ingredients = web.list_ingredients()

    assert [ingredient.model_dump() for ingredient in ingredients] == [
        {
            "ingredient_id": "ingredient_scallion",
            "name": "Scallion",
            "slug": "scallion",
            "aliases": ["green onion"],
            "default_unit": "bunch",
        }
    ]


def test_parse_ingredient_lines_returns_ordered_editor_projections():
    projections = web.parse_ingredient_lines(
        web.IngredientLineParseRequest(lines=["1/2 cup flour", "salt to taste"])
    )

    assert projections[0].safe_for_rich is True
    assert projections[0].quantity_text == "1/2"
    assert projections[0].ingredient_name == "flour"
    assert projections[1].safe_for_rich is False
    assert projections[1].raw_text == "salt to taste"


def test_list_recipes_openapi_response_uses_recipe_card_dto():
    schema = web.app.openapi()

    response_schema = schema["paths"]["/api/recipes"]["get"]["responses"]["200"]
    response_schema = response_schema["content"]["application/json"]["schema"]

    assert response_schema["type"] == "array"
    assert response_schema["items"] == {
        "$ref": "#/components/schemas/RecipeCardDto"
    }


def test_get_recipe_detail_delegates_and_shapes_response(monkeypatch):
    class FakeRecipesAPI:
        def __init__(self):
            self.requested_recipe_id = None

        def get_detail(self, recipe_id):
            self.requested_recipe_id = recipe_id
            return {
                "recipe": {
                    "recipe_id": recipe_id,
                    "title": "Tomato Soup",
                    "slug": "tomato-soup",
                    "servings": 4,
                    "source_name": "KitchenSync Test",
                    "source_url": "https://example.com/tomato-soup",
                    "author": "Test Author",
                    "imported_from": "manual-test",
                    "time_estimate_minutes": 45,
                    "main_image_path": "recipes/tomato-soup/images/main.jpg",
                    "markdown_path": "recipes/tomato-soup/recipe.md",
                    "created_at": "2026-07-14 12:00:00",
                    "updated_at": "2026-07-14 12:00:00",
                        "tags": ["soup", "weeknight"],
                        "description": "A smooth tomato soup.",
                        "notes": ["Use ripe tomatoes."],
                },
                "ingredients": [
                    {
                        "ingredient_order": 1,
                        "raw_text": "6 Roma tomatoes, diced",
                        "ingredient_id": "ingredient_roma_tomato",
                        "parsed_name": "Roma Tomato",
                        "quantity_amount": 6,
                        "quantity_unit": "unit",
                        "preparation": "diced",
                    }
                ],
                "steps": [
                    {
                        "step_order": 1,
                        "text": "Simmer tomatoes.",
                    }
                ],
            }

    fake_recipes = FakeRecipesAPI()

    class FakeKitchenSync:
        def __init__(self):
            self.recipes = fake_recipes
            self.cookbook = FakeCookbookAPI()
            self.closed = False

        def __enter__(self):
            return self

        def __exit__(self, *exc_info):
            self.closed = True

    fake_kitchen_sync = FakeKitchenSync()

    class FakeKitchenSyncApp:
        @staticmethod
        def open():
            return fake_kitchen_sync

    monkeypatch.setattr(web, "KitchenSyncApp", FakeKitchenSyncApp)

    detail = web.get_recipe_detail("recipe_tomato_soup")

    assert detail.model_dump() == {
        "recipe": {
            "recipe_id": "recipe_tomato_soup",
            "title": "Tomato Soup",
            "slug": "tomato-soup",
            "servings": 4,
            "source_name": "KitchenSync Test",
            "source_url": "https://example.com/tomato-soup",
            "author": "Test Author",
            "imported_from": "manual-test",
            "time_estimate_minutes": 45,
            "image_url": "/library/recipes/tomato-soup/images/main.jpg",
            "tags": ["soup", "weeknight"],
            "description": "A smooth tomato soup.",
            "notes": ["Use ripe tomatoes."],
        },
        "ingredients": [
            {
                "ingredient_order": 1,
                "raw_text": "6 Roma tomatoes, diced",
                "ingredient_id": "ingredient_roma_tomato",
                "parsed_name": "Roma Tomato",
                "quantity_amount": 6.0,
                "quantity_unit": "unit",
                "preparation": "diced",
            }
        ],
        "steps": [
            {
                "step_order": 1,
                "text": "Simmer tomatoes.",
            }
        ],
        "cookbook": None,
    }
    assert fake_recipes.requested_recipe_id == "recipe_tomato_soup"
    assert fake_kitchen_sync.closed is True


def test_get_recipe_detail_returns_404_for_missing_recipe(monkeypatch):
    class FakeRecipesAPI:
        def get_detail(self, recipe_id):
            return None

    class FakeKitchenSync:
        def __init__(self):
            self.recipes = FakeRecipesAPI()
            self.cookbook = FakeCookbookAPI()
            self.closed = False

        def __enter__(self):
            return self

        def __exit__(self, *exc_info):
            self.closed = True

    fake_kitchen_sync = FakeKitchenSync()

    class FakeKitchenSyncApp:
        @staticmethod
        def open():
            return fake_kitchen_sync

    monkeypatch.setattr(web, "KitchenSyncApp", FakeKitchenSyncApp)

    with pytest.raises(HTTPException) as exc_info:
        web.get_recipe_detail("missing")

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Recipe not found"
    assert fake_kitchen_sync.closed is True


def test_get_recipe_detail_openapi_response_uses_recipe_detail_dto():
    schema = web.app.openapi()

    responses = schema["paths"]["/api/recipes/{recipe_id}"]["get"]["responses"]
    response_schema = responses["200"]["content"]["application/json"]["schema"]

    assert response_schema == {
        "$ref": "#/components/schemas/RecipeDetailDto"
    }
    assert responses["404"]["description"] == "Recipe not found"


def test_cookbook_membership_metadata_and_recipe_edit_http_flow(tmp_path, monkeypatch):
    database_path = tmp_path / "library" / "kitchensync.sqlite"
    with KitchenSyncApp.open(database_path) as app:
        app.recipes.save_imported_recipe(
            Recipe(
                name="Tomato Soup",
                ingredients=[
                    RecipeIngredient(ingredient=Ingredient(name="Tomato"))
                ],
                steps=[RecipeStep(order=1, text="Simmer the tomatoes.")],
            )
        )
        recipe_id = app.recipes.list()[0]["recipe_id"]

    class TempKitchenSyncApp:
        @staticmethod
        def open():
            return KitchenSyncApp.open(database_path)

    monkeypatch.setattr(web, "KitchenSyncApp", TempKitchenSyncApp)
    assert web.list_recipes(scope="cookbook") == []

    added = web.add_recipe_to_cookbook(recipe_id)
    assert added.model_dump() == {
        "favorite": False,
        "rating": None,
        "notes": None,
    }

    saved_metadata = web.update_cookbook_entry(
        recipe_id,
        web.CookbookUpdateRequest(
            favorite=True,
            rating=4,
            notes="Try basil next time.",
        ),
    )
    assert saved_metadata.favorite is True
    assert web.add_recipe_to_cookbook(recipe_id).model_dump() == {
        "favorite": True,
        "rating": 4,
        "notes": "Try basil next time.",
    }

    cookbook_cards = web.list_recipes(scope="cookbook")
    assert cookbook_cards[0].cookbook is not None
    assert cookbook_cards[0].cookbook.model_dump() == {
        "favorite": True,
        "rating": 4,
    }

    saved_recipe = web.update_recipe(
        recipe_id,
        web.RecipeUpdateRequest(
            title="Roasted Tomato Soup",
            description="A rich weeknight soup.",
            servings=6,
            time_estimate_minutes=50,
            tags=["dinner", "vegetarian"],
            ingredients=["8 Roma tomatoes, roasted", "2 cups stock"],
            steps=["Roast the tomatoes.", "Blend until smooth."],
            notes=["Add cream when serving."],
        ),
    )
    assert saved_recipe.recipe.title == "Roasted Tomato Soup"
    assert saved_recipe.cookbook is not None
    assert saved_recipe.cookbook.model_dump() == {
        "favorite": True,
        "rating": 4,
        "notes": "Try basil next time.",
    }

    recipe_text = (
        database_path.parent / "recipes" / "tomato-soup" / "recipe.md"
    ).read_text(encoding="utf-8")
    cookbook_text = (
        database_path.parent / "cookbook" / "tomato-soup.md"
    ).read_text(encoding="utf-8")
    assert recipe_text.startswith("# Roasted Tomato Soup\n")
    assert "- Time: 50 minutes" in recipe_text
    assert cookbook_text.startswith("# Roasted Tomato Soup\n")
    assert "- Favorite: yes" in cookbook_text
