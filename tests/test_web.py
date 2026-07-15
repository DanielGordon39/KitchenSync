from kitchensync import web


def test_list_recipes_delegates_and_shapes_recipe_cards(monkeypatch):
    class FakeRecipesAPI:
        def list(self):
            return [
                {
                    "recipe_id": "recipe_tomato_soup",
                    "title": "Tomato Soup",
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
            "image_url": None,
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
