from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi import HTTPException

from kitchensync import KitchenSyncApp
from kitchensync import web
from kitchensync.models import Ingredient, Recipe, RecipeIngredient, RecipeMetadata, RecipeStep
from kitchensync.parsing import InstagramSource, validate_instagram_url


CASE_DIR = (
    Path(__file__).parents[1]
    / "scratch"
    / "archive"
    / "instagram"
    / "social_recipe_cases"
)


@pytest.mark.parametrize(
    ("filename", "complete"),
    [
        ("014-korean-spicy-tofu-stew-meal-prep.json", True),
        ("006-stealth-health-cookbook-promotion.json", False),
    ],
)
def test_preview_returns_frozen_draft_without_library_writes(
    filename, complete, tmp_path, monkeypatch
):
    case = _load_case(filename)
    database_path = tmp_path / "library" / "kitchensync.sqlite"
    with KitchenSyncApp.open(database_path):
        pass
    files_before = _library_files(database_path.parent)
    _use_database(monkeypatch, database_path)
    monkeypatch.setattr(
        web,
        "acquire_instagram_source",
        lambda _url: _source(case),
    )

    preview = web.preview_recipe_import(
        web.RecipeImportPreviewRequest(source_url=case["source_url"])
    )

    assert preview.draft.model_dump(
        include={"title", "servings", "ingredients", "steps", "tags"}
    ) == {
        "title": case["expected"]["name"] or "",
        "servings": case["expected"]["servings"],
        "ingredients": case["expected"]["raw_ingredients"],
        "steps": case["expected"]["steps"],
        "tags": case["expected"]["tags"],
    }
    assert preview.complete is complete
    assert preview.raw_source_description == case["source_text"]
    assert preview.existing_recipe_matches == []
    with KitchenSyncApp.open(database_path) as app:
        assert app.recipes.list() == []
        assert app.ingredients.list() == []
    assert _library_files(database_path.parent) == files_before


def test_preview_reports_source_and_slug_duplicate(tmp_path, monkeypatch):
    case = _load_case("014-korean-spicy-tofu-stew-meal-prep.json")
    database_path = tmp_path / "library" / "kitchensync.sqlite"
    with KitchenSyncApp.open(database_path) as app:
        app.recipes.save_imported_recipe(
            Recipe(
                name=case["expected"]["name"],
                ingredients=[
                    RecipeIngredient(ingredient=Ingredient(name="Silken Tofu"))
                ],
                steps=[RecipeStep(order=1, text="Cook the stew.")],
                metadata=RecipeMetadata(source_url=case["source_url"]),
            )
        )
    _use_database(monkeypatch, database_path)
    monkeypatch.setattr(web, "acquire_instagram_source", lambda _url: _source(case))

    preview = web.preview_recipe_import(
        web.RecipeImportPreviewRequest(source_url=case["source_url"])
    )

    assert len(preview.existing_recipe_matches) == 1
    assert preview.existing_recipe_matches[0].matched_by == ["source_url", "slug"]


def test_instagram_url_validation_accepts_only_posts_and_reels():
    assert validate_instagram_url(
        "https://www.instagram.com/creator/reel/example-id/"
    ).endswith("/example-id/")

    with pytest.raises(ValueError, match="public Instagram post or reel"):
        validate_instagram_url("https://www.youtube.com/shorts/example-id")
    with pytest.raises(ValueError, match="public Instagram post or reel"):
        validate_instagram_url("https://www.instagram.com/creator/")


def test_preview_returns_reviewable_acquisition_error(monkeypatch):
    def fail_acquisition(_url):
        raise RuntimeError("private post")

    monkeypatch.setattr(web, "acquire_instagram_source", fail_acquisition)

    with pytest.raises(HTTPException) as exc_info:
        web.preview_recipe_import(
            web.RecipeImportPreviewRequest(
                source_url="https://www.instagram.com/reel/example-id/"
            )
        )

    assert exc_info.value.status_code == 502
    assert "acquisition failed" in exc_info.value.detail


def _load_case(filename: str) -> dict:
    return json.loads((CASE_DIR / filename).read_text(encoding="utf-8"))


def _source(case: dict) -> InstagramSource:
    return InstagramSource(
        description=case["source_text"],
        author=case.get("creator"),
        source_name="Instagram",
        source_url=case["source_url"],
        thumbnail_url="https://example.com/thumbnail.jpg",
    )


def _use_database(monkeypatch, database_path: Path) -> None:
    class TempKitchenSyncApp:
        @staticmethod
        def open():
            return KitchenSyncApp.open(database_path)

    monkeypatch.setattr(web, "KitchenSyncApp", TempKitchenSyncApp)


def _library_files(library_root: Path) -> list[str]:
    return sorted(
        path.relative_to(library_root).as_posix()
        for path in library_root.rglob("*")
        if path.is_file() and path.name != "kitchensync.sqlite"
    )
