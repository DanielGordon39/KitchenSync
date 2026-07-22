from __future__ import annotations

import pytest
from fastapi import HTTPException

from kitchensync import KitchenSyncApp
from kitchensync import recipe_api, web


def test_reviewed_import_delegates_once_and_persists_markdown_sqlite_and_image(
    tmp_path, monkeypatch
):
    database_path = tmp_path / "library" / "kitchensync.sqlite"
    _use_database(monkeypatch, database_path)
    monkeypatch.setattr(
        recipe_api,
        "_fetch_image",
        lambda _uri: (b"reviewed image", "image/jpeg"),
    )
    calls = _spy_on_import_boundary(monkeypatch)

    detail = web.save_recipe_import(_request())

    assert calls == ["Reviewed Tomato Soup"]
    assert detail.recipe.title == "Reviewed Tomato Soup"
    assert detail.recipe.image_url == (
        "/library/recipes/reviewed-tomato-soup/images/main.jpg"
    )
    assert detail.recipe.source_name == "Instagram"
    assert detail.recipe.author == "Test Cook"
    assert detail.recipe.imported_from == "yt-dlp"
    library_root = database_path.parent
    recipe_path = library_root / "recipes" / "reviewed-tomato-soup" / "recipe.md"
    assert recipe_path.exists()
    assert "![Main recipe image](images/main.jpg)" in recipe_path.read_text(
        encoding="utf-8"
    )
    assert (
        library_root
        / "recipes"
        / "reviewed-tomato-soup"
        / "images"
        / "main.jpg"
    ).read_bytes() == b"reviewed image"
    assert sorted(path.name for path in (library_root / "ingredients").glob("*.md")) == [
        "butter.md",
        "roma-tomato.md",
    ]
    with KitchenSyncApp.open(database_path) as app:
        assert [row["title"] for row in app.recipes.list()] == [
            "Reviewed Tomato Soup"
        ]
        assert [row["name"] for row in app.ingredients.list()] == [
            "Butter",
            "Roma Tomato",
        ]


def test_duplicate_import_requires_explicit_update(tmp_path, monkeypatch):
    database_path = tmp_path / "library" / "kitchensync.sqlite"
    _use_database(monkeypatch, database_path)
    monkeypatch.setattr(recipe_api, "_fetch_image", lambda _uri: (b"", None))
    calls = _spy_on_import_boundary(monkeypatch)
    request = _request(thumbnail_url=None)
    web.save_recipe_import(request)

    with pytest.raises(HTTPException) as exc_info:
        web.save_recipe_import(request)

    assert exc_info.value.status_code == 409
    assert calls == ["Reviewed Tomato Soup"]

    updated = web.save_recipe_import(
        request.model_copy(
            update={
                "duplicate_action": "update",
                "draft": request.draft.model_copy(
                    update={"description": "Updated after explicit review."}
                ),
            }
        )
    )

    assert updated.recipe.description == "Updated after explicit review."
    assert calls == ["Reviewed Tomato Soup", "Reviewed Tomato Soup"]
    with KitchenSyncApp.open(database_path) as app:
        assert len(app.recipes.list()) == 1


def test_import_survives_thumbnail_download_failure(tmp_path, monkeypatch):
    database_path = tmp_path / "library" / "kitchensync.sqlite"
    _use_database(monkeypatch, database_path)

    def fail_image(_uri):
        raise OSError("image unavailable")

    monkeypatch.setattr(recipe_api, "_fetch_image", fail_image)

    detail = web.save_recipe_import(_request())

    assert detail.recipe.image_url is None
    assert (
        database_path.parent
        / "recipes"
        / "reviewed-tomato-soup"
        / "recipe.md"
    ).exists()


def _request(*, thumbnail_url="https://example.com/tomato.jpg"):
    return web.RecipeImportRequest(
        draft=web.RecipeUpdateRequest(
            title="Reviewed Tomato Soup",
            description="A reviewed import.",
            servings=4,
            time_estimate_minutes=35,
            tags=["dinner", "soup"],
            ingredients=["6 Roma Tomato", "2 tbsp Butter"],
            steps=["Roast the tomatoes.", "Blend until smooth."],
            notes=["Check seasoning."],
        ),
        source_url="https://www.instagram.com/reel/reviewed-example/",
        source_name="Instagram",
        author="Test Cook",
        thumbnail_url=thumbnail_url,
        duplicate_action="import",
    )


def _use_database(monkeypatch, database_path):
    class TempKitchenSyncApp:
        @staticmethod
        def open():
            return KitchenSyncApp.open(database_path)

    monkeypatch.setattr(web, "KitchenSyncApp", TempKitchenSyncApp)


def _spy_on_import_boundary(monkeypatch):
    calls = []
    original = recipe_api.RecipesAPI.save_imported_recipe

    def save(self, recipe):
        calls.append(recipe.name)
        return original(self, recipe)

    monkeypatch.setattr(recipe_api.RecipesAPI, "save_imported_recipe", save)
    return calls
