import pytest
from fastapi import HTTPException

from kitchensync import web


def test_list_recipes_delegates_and_shapes_recipe_cards(monkeypatch):
    class FakeRecipesAPI:
        def list(self):
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
        }
    ]
    assert fake_kitchen_sync.closed is True


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
