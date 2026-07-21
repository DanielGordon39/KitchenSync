from __future__ import annotations

from difflib import SequenceMatcher
import mimetypes
from pathlib import Path
import re
import sqlite3
from typing import Any
from urllib.parse import urlparse
from urllib.request import Request, urlopen
from uuid import uuid4

from .database import row_dict, rows
from .markdown import (
    ingredient_to_markdown,
    raw_ingredient_text,
    recipe_to_markdown,
    slugify,
)
from .models import Ingredient, Recipe

IMAGE_EXTENSIONS = {".gif", ".jpeg", ".jpg", ".png", ".webp"}
MIN_SEARCH_SCORE = 0.45


def _fetch_image(uri: str) -> tuple[bytes, str | None]:
    request = Request(
        uri,
        headers={"User-Agent": "KitchenSync/0.1 recipe image fetcher"},
    )
    with urlopen(request, timeout=15) as response:
        content_type = response.headers.get_content_type()
        return response.read(), content_type


def _time_estimate_minutes(recipe: Recipe) -> int | None:
    if recipe.time_estimate is None:
        return None

    return recipe.time_estimate.base_minutes


class RecipesAPI:
    def __init__(self, connection: sqlite3.Connection, library_root: Path):
        self.connection = connection
        self.library_root = library_root

    def save_imported_recipe(self, recipe: Recipe) -> None:
        slug = slugify(recipe.name)
        recipe_id = self._recipe_id_for_import(recipe, slug)
        main_image_path = self._save_main_image(recipe, slug)
        if main_image_path is None:
            main_image_path = self._existing_main_image_path(recipe_id)

        self._write_recipe_file(recipe, slug, main_image_path)
        self._ensure_ingredient_files_and_rows(recipe)
        self._upsert_recipe_row(
            recipe_id=recipe_id,
            title=recipe.name,
            slug=slug,
            servings=recipe.servings,
            source_name=recipe.metadata.source_name,
            source_url=recipe.metadata.source_url,
            author=recipe.metadata.author,
            imported_from=recipe.metadata.imported_from,
            time_estimate_minutes=_time_estimate_minutes(recipe),
            main_image_path=main_image_path,
            markdown_path=f"recipes/{slug}/recipe.md",
        )
        self._replace_recipe_ingredient_rows(recipe_id, recipe)
        self._replace_recipe_step_rows(recipe_id, recipe)
        self._replace_recipe_tag_rows(recipe_id, recipe)
        self._upsert_recipe_search(
            recipe_id,
            [
                recipe.name,
                slug,
                recipe.metadata.source_name,
                recipe.metadata.source_url,
                recipe.metadata.author,
                recipe.metadata.imported_from,
                *recipe.tags,
                *(item.ingredient.name for item in recipe.ingredients),
                *(raw_ingredient_text(item) for item in recipe.ingredients),
            ],
        )

        self.connection.commit()

    def update_recipe(self, recipe_id: str, recipe: Recipe) -> dict[str, Any] | None:
        existing = self.get(recipe_id)
        if existing is None:
            return None

        slug = existing.get("slug") or slugify(recipe.name)
        markdown_path = existing.get("markdown_path") or f"recipes/{slug}/recipe.md"
        main_image_path = existing.get("main_image_path")

        self._write_recipe_file(
            recipe,
            slug,
            main_image_path,
            markdown_path=markdown_path,
        )
        self._ensure_ingredient_files_and_rows(recipe)
        self._upsert_recipe_row(
            recipe_id=recipe_id,
            title=recipe.name,
            slug=slug,
            servings=recipe.servings,
            source_name=recipe.metadata.source_name,
            source_url=recipe.metadata.source_url,
            author=recipe.metadata.author,
            imported_from=recipe.metadata.imported_from,
            time_estimate_minutes=_time_estimate_minutes(recipe),
            main_image_path=main_image_path,
            markdown_path=markdown_path,
        )
        self._replace_recipe_ingredient_rows(recipe_id, recipe)
        self._replace_recipe_step_rows(recipe_id, recipe)
        self._replace_recipe_tag_rows(recipe_id, recipe)
        self._upsert_recipe_search(
            recipe_id,
            [
                recipe.name,
                slug,
                recipe.metadata.source_name,
                recipe.metadata.source_url,
                recipe.metadata.author,
                recipe.metadata.imported_from,
                *recipe.tags,
                *(item.ingredient.name for item in recipe.ingredients),
                *(raw_ingredient_text(item) for item in recipe.ingredients),
            ],
        )
        self.connection.commit()
        return self.get_detail(recipe_id)

    def _recipe_id_for_import(self, recipe: Recipe, slug: str) -> str:
        if recipe.metadata.source_url:
            row = self.connection.execute(
                """
                SELECT recipe_id
                FROM recipe_recipes
                WHERE source_url = ?
                ORDER BY created_at
                LIMIT 1
                """,
                (recipe.metadata.source_url,),
            ).fetchone()
            if row is not None:
                return row["recipe_id"]

        row = self.connection.execute(
            """
            SELECT recipe_id
            FROM recipe_recipes
            WHERE slug = ?
            ORDER BY created_at
            LIMIT 1
            """,
            (slug,),
        ).fetchone()
        if row is not None:
            return row["recipe_id"]

        return uuid4().hex

    def save_metadata(
        self,
        *,
        recipe_id: str,
        title: str,
        slug: str | None = None,
        servings: int | None = None,
        source_name: str | None = None,
        source_url: str | None = None,
        author: str | None = None,
        imported_from: str | None = None,
        time_estimate_minutes: int | None = None,
        main_image_path: str | None = None,
        markdown_path: str | None = None,
    ) -> None:
        self._upsert_recipe_row(
            recipe_id=recipe_id,
            title=title,
            slug=slug,
            servings=servings,
            source_name=source_name,
            source_url=source_url,
            author=author,
            imported_from=imported_from,
            time_estimate_minutes=time_estimate_minutes,
            main_image_path=main_image_path,
            markdown_path=markdown_path,
        )
        self._upsert_recipe_search(
            recipe_id,
            [title, slug, source_name, source_url, author, imported_from],
        )
        self.connection.commit()

    def _write_recipe_file(
        self,
        recipe: Recipe,
        slug: str,
        main_image_path: str | None,
        *,
        markdown_path: str | None = None,
    ) -> None:
        recipe_path = self.library_root / (
            markdown_path or f"recipes/{slug}/recipe.md"
        )
        recipe_path.parent.mkdir(parents=True, exist_ok=True)
        recipe_path.write_text(
            recipe_to_markdown(
                recipe,
                main_image_path=_markdown_image_path(slug, main_image_path),
            ),
            encoding="utf-8",
        )

    def _save_main_image(self, recipe: Recipe, slug: str) -> str | None:
        image = next((image for image in recipe.metadata.images if image.uri), None)
        if image is None:
            return None

        try:
            content, content_type = _fetch_image(image.uri)
        except Exception:
            return None

        if not content:
            return None

        relative_path = Path("recipes") / slug / "images" / (
            "main" + _image_extension(image.uri, content_type)
        )
        image_path = self.library_root / relative_path
        image_path.parent.mkdir(parents=True, exist_ok=True)
        image_path.write_bytes(content)
        return relative_path.as_posix()

    def _existing_main_image_path(self, recipe_id: str) -> str | None:
        row = self.connection.execute(
            """
            SELECT main_image_path
            FROM recipe_recipes
            WHERE recipe_id = ?
            """,
            (recipe_id,),
        ).fetchone()
        if row is None:
            return None

        return row["main_image_path"]

    def _ensure_ingredient_files_and_rows(self, recipe: Recipe) -> None:
        ingredient_dir = self.library_root / "ingredients"
        ingredient_dir.mkdir(parents=True, exist_ok=True)

        seen_slugs: set[str] = set()
        for item in recipe.ingredients:
            slug = slugify(item.ingredient.name)
            if slug in seen_slugs:
                continue
            seen_slugs.add(slug)

            ingredient_id = self._find_ingredient_id(item.ingredient.name)
            if ingredient_id is not None:
                existing = self.connection.execute(
                    "SELECT slug FROM ingredient_ingredients WHERE ingredient_id = ?",
                    (ingredient_id,),
                ).fetchone()
                if existing["slug"] != slug:
                    continue
            else:
                ingredient_id = uuid4().hex
            ingredient_path = ingredient_dir / f"{slug}.md"

            if not ingredient_path.exists():
                ingredient_path.write_text(
                    ingredient_to_markdown(Ingredient(name=item.ingredient.name)),
                    encoding="utf-8",
                )

            self.connection.execute(
                """
                INSERT INTO ingredient_ingredients (ingredient_id, name, slug)
                VALUES (?, ?, ?)
                ON CONFLICT(ingredient_id) DO UPDATE SET
                    name = excluded.name,
                    slug = excluded.slug
                """,
                (ingredient_id, item.ingredient.name, slug),
            )

    def _find_ingredient_id(self, name: str) -> str | None:
        slug = slugify(name)
        row = self.connection.execute(
            """
            SELECT ingredients.ingredient_id
            FROM ingredient_ingredients AS ingredients
            LEFT JOIN ingredient_aliases AS aliases
                ON aliases.ingredient_id = ingredients.ingredient_id
            WHERE ingredients.slug = ? OR lower(aliases.alias) = lower(?)
            ORDER BY CASE WHEN ingredients.slug = ? THEN 0 ELSE 1 END
            LIMIT 1
            """,
            (slug, name.strip(), slug),
        ).fetchone()
        if row is not None:
            return row["ingredient_id"]
        return None

    def _upsert_recipe_row(
        self,
        *,
        recipe_id: str,
        title: str,
        slug: str | None = None,
        servings: int | None = None,
        source_name: str | None = None,
        source_url: str | None = None,
        author: str | None = None,
        imported_from: str | None = None,
        time_estimate_minutes: int | None = None,
        main_image_path: str | None = None,
        markdown_path: str | None = None,
    ) -> None:
        self.connection.execute(
            """
            INSERT INTO recipe_recipes (
                recipe_id,
                title,
                slug,
                servings,
                source_name,
                source_url,
                author,
                imported_from,
                time_estimate_minutes,
                main_image_path,
                markdown_path
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(recipe_id) DO UPDATE SET
                title = excluded.title,
                slug = excluded.slug,
                servings = excluded.servings,
                source_name = excluded.source_name,
                source_url = excluded.source_url,
                author = excluded.author,
                imported_from = excluded.imported_from,
                time_estimate_minutes = excluded.time_estimate_minutes,
                main_image_path = excluded.main_image_path,
                markdown_path = excluded.markdown_path,
                updated_at = CURRENT_TIMESTAMP
            """,
            (
                recipe_id,
                title,
                slug,
                servings,
                source_name,
                source_url,
                author,
                imported_from,
                time_estimate_minutes,
                main_image_path,
                markdown_path,
            ),
        )

    def _replace_recipe_ingredient_rows(self, recipe_id: str, recipe: Recipe) -> None:
        self.connection.execute(
            "DELETE FROM recipe_ingredients WHERE recipe_id = ?",
            (recipe_id,),
        )

        for index, item in enumerate(recipe.ingredients, start=1):
            quantity = item.quantity
            ingredient_id = self._find_ingredient_id(item.ingredient.name)
            if ingredient_id is None:
                raise RuntimeError("Ingredient row missing after ingredient setup")

            self.connection.execute(
                """
                INSERT INTO recipe_ingredients (
                    recipe_id,
                    ingredient_order,
                    raw_text,
                    ingredient_id,
                    parsed_name,
                    quantity_amount,
                    quantity_unit,
                    preparation
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    recipe_id,
                    index,
                    raw_ingredient_text(item),
                    ingredient_id,
                    item.ingredient.name,
                    quantity.amount if quantity else None,
                    quantity.unit if quantity else None,
                    item.preparation,
                ),
            )

    def _replace_recipe_step_rows(self, recipe_id: str, recipe: Recipe) -> None:
        self.connection.execute(
            "DELETE FROM recipe_steps WHERE recipe_id = ?",
            (recipe_id,),
        )

        for step in recipe.steps:
            self.connection.execute(
                """
                INSERT INTO recipe_steps (recipe_id, step_order, text)
                VALUES (?, ?, ?)
                """,
                (recipe_id, step.order, step.text),
            )

    def _replace_recipe_tag_rows(self, recipe_id: str, recipe: Recipe) -> None:
        self.connection.execute(
            "DELETE FROM recipe_tags WHERE recipe_id = ?",
            (recipe_id,),
        )

        for index, tag in enumerate(recipe.tags, start=1):
            self.connection.execute(
                """
                INSERT INTO recipe_tags (recipe_id, tag_order, tag_slug)
                VALUES (?, ?, ?)
                """,
                (recipe_id, index, tag),
            )

    def _upsert_recipe_search(
        self,
        recipe_id: str,
        values: list[str | None],
    ) -> None:
        search_text = " ".join(value for value in values if value)
        self.connection.execute(
            """
            INSERT INTO recipe_search (recipe_id, search_text)
            VALUES (?, ?)
            ON CONFLICT(recipe_id) DO UPDATE SET search_text = excluded.search_text
            """,
            (recipe_id, search_text),
        )

    def get(self, recipe_id: str) -> dict[str, Any] | None:
        row = self.connection.execute(
            "SELECT * FROM recipe_recipes WHERE recipe_id = ?",
            (recipe_id,),
        ).fetchone()
        return self._recipe_row(row)

    def get_by_slug(self, slug: str) -> dict[str, Any] | None:
        row = self.connection.execute(
            "SELECT * FROM recipe_recipes WHERE slug = ?",
            (slug,),
        ).fetchone()
        return self._recipe_row(row)

    def list(self, recipe_ids: set[str] | None = None) -> list[dict[str, Any]]:
        recipe_rows = self.connection.execute(
            """
            SELECT *
            FROM recipe_recipes
            ORDER BY lower(title)
            """
        ).fetchall()
        return [
            self._recipe_row(row)
            for row in recipe_rows
            if row is not None
            and (recipe_ids is None or row["recipe_id"] in recipe_ids)
        ]

    def get_detail(self, recipe_id: str) -> dict[str, Any] | None:
        recipe = self.get(recipe_id)
        if recipe is None:
            return None

        ingredients = self.connection.execute(
            """
            SELECT
                ingredient_order,
                raw_text,
                ingredient_id,
                parsed_name,
                quantity_amount,
                quantity_unit,
                preparation
            FROM recipe_ingredients
            WHERE recipe_id = ?
            ORDER BY ingredient_order
            """,
            (recipe_id,),
        ).fetchall()
        steps = self.connection.execute(
            """
            SELECT step_order, text
            FROM recipe_steps
            WHERE recipe_id = ?
            ORDER BY step_order
            """,
            (recipe_id,),
        ).fetchall()

        markdown_fields = self._markdown_fields(recipe.get("markdown_path"))
        recipe["description"] = markdown_fields["description"]
        recipe["notes"] = markdown_fields["notes"]

        return {
            "recipe": recipe,
            "ingredients": rows(ingredients),
            "steps": rows(steps),
        }

    def _markdown_fields(self, markdown_path: str | None) -> dict[str, Any]:
        result: dict[str, Any] = {"description": None, "notes": []}
        if not markdown_path:
            return result

        library_root = self.library_root.resolve()
        path = (library_root / markdown_path).resolve()
        if not path.is_relative_to(library_root) or not path.is_file():
            return result

        lines = path.read_text(encoding="utf-8").splitlines()
        if lines and lines[0].startswith("# "):
            description_lines = []
            for line in lines[1:]:
                if line.startswith("- ") or line.startswith("## "):
                    break
                description_lines.append(line)
            description = "\n".join(description_lines).strip()
            result["description"] = description or None

        try:
            notes_index = lines.index("## Notes")
        except ValueError:
            return result

        notes = []
        for line in lines[notes_index + 1 :]:
            if line.startswith("## "):
                break
            if line.startswith("- "):
                notes.append(line.removeprefix("- ").strip())
        result["notes"] = notes
        return result

    def search(
        self,
        query: str,
        *,
        exact_tags: list[str] | None = None,
        meal_tags: list[str] | None = None,
        cuisine_tags: list[str] | None = None,
        diet_tags: list[str] | None = None,
        recipe_ids: set[str] | None = None,
    ) -> list[dict[str, Any]]:
        query = query.strip()
        exact_tag_set = _tag_set(exact_tags)
        meal_tag_set = _tag_set(meal_tags)
        cuisine_tag_set = _tag_set(cuisine_tags)
        diet_tag_set = _tag_set(diet_tags)

        recipe_rows = self.connection.execute(
            "SELECT * FROM recipe_recipes"
        ).fetchall()
        tag_rows = self.connection.execute(
            "SELECT recipe_id, tag_slug FROM recipe_tags ORDER BY tag_order"
        ).fetchall()
        ingredient_rows = self.connection.execute(
            """
            SELECT recipe_id, parsed_name, raw_text
            FROM recipe_ingredients
            ORDER BY ingredient_order
            """
        ).fetchall()

        tags_by_recipe: dict[str, list[str]] = {}
        for row in tag_rows:
            tags_by_recipe.setdefault(row["recipe_id"], []).append(row["tag_slug"])

        ingredients_by_recipe: dict[str, list[str]] = {}
        for row in ingredient_rows:
            values = ingredients_by_recipe.setdefault(row["recipe_id"], [])
            if row["parsed_name"]:
                values.append(row["parsed_name"])
            values.append(row["raw_text"])

        ranked: list[tuple[int, int, float, str, str, dict[str, Any]]] = []
        for row in recipe_rows:
            recipe = row_dict(row)
            if recipe is None:
                continue

            recipe_id = recipe["recipe_id"]
            if recipe_ids is not None and recipe_id not in recipe_ids:
                continue
            tags = tags_by_recipe.get(recipe_id, [])
            tag_set = set(tags)

            if meal_tag_set and not tag_set.intersection(meal_tag_set):
                continue
            if cuisine_tag_set and not tag_set.intersection(cuisine_tag_set):
                continue
            if diet_tag_set and not diet_tag_set.issubset(tag_set):
                continue

            matched_tag_count = len(tag_set.intersection(exact_tag_set))
            tag_match: str | None = None
            tag_group = 0
            if exact_tag_set:
                if matched_tag_count == 0:
                    continue
                tag_match = (
                    "all" if matched_tag_count == len(exact_tag_set) else "some"
                )
                tag_group = 0 if tag_match == "all" else 1

            relevance = _recipe_search_score(
                query,
                recipe,
                tags,
                ingredients_by_recipe.get(recipe_id, []),
            )
            if query and relevance < MIN_SEARCH_SCORE:
                continue

            recipe["tags"] = tags
            recipe["tag_match"] = tag_match
            ranked.append(
                (
                    tag_group,
                    -matched_tag_count,
                    -relevance,
                    recipe["title"].casefold(),
                    recipe_id,
                    recipe,
                )
            )

        # ponytail: score the local catalog in memory; add FTS/paging when its
        # size makes this measurably slow.
        ranked.sort(key=lambda item: item[:-1])
        return [item[-1] for item in ranked]

    def list_tags(self, recipe_ids: set[str] | None = None) -> list[dict[str, Any]]:
        tag_rows = self.connection.execute(
            """
            SELECT recipe_id, tag_slug
            FROM recipe_tags
            ORDER BY tag_slug, recipe_id
            """
        ).fetchall()
        counts: dict[str, int] = {}
        for row in tag_rows:
            if recipe_ids is not None and row["recipe_id"] not in recipe_ids:
                continue
            counts[row["tag_slug"]] = counts.get(row["tag_slug"], 0) + 1
        return [
            {"tag_slug": tag_slug, "recipe_count": count}
            for tag_slug, count in sorted(counts.items())
        ]

    def _recipe_row(self, row: sqlite3.Row | None) -> dict[str, Any] | None:
        recipe = row_dict(row)
        if recipe is None:
            return None

        recipe["tags"] = self._recipe_tags(recipe["recipe_id"])
        return recipe

    def _recipe_tags(self, recipe_id: str) -> list[str]:
        tag_rows = self.connection.execute(
            """
            SELECT tag_slug
            FROM recipe_tags
            WHERE recipe_id = ?
            ORDER BY tag_order
            """,
            (recipe_id,),
        ).fetchall()
        return [row["tag_slug"] for row in tag_rows]


def _image_extension(uri: str, content_type: str | None) -> str:
    if content_type:
        guessed = mimetypes.guess_extension(content_type)
        if guessed == ".jpe":
            guessed = ".jpg"
        if guessed in IMAGE_EXTENSIONS:
            return guessed

    suffix = Path(urlparse(uri).path).suffix.lower()
    return suffix if suffix in IMAGE_EXTENSIONS else ".jpg"


def _markdown_image_path(slug: str, main_image_path: str | None) -> str | None:
    if not main_image_path:
        return None

    prefix = f"recipes/{slug}/"
    return main_image_path.removeprefix(prefix)


def _tag_set(values: list[str] | None) -> set[str]:
    return {
        slugify(value.lstrip("#"))
        for value in values or []
        if value.strip().lstrip("#")
    }


def _search_text(value: str | None) -> str:
    return re.sub(r"[^a-z0-9]+", " ", (value or "").casefold()).strip()


def _fuzzy_score(query: str, candidate: str | None) -> float:
    normalized_query = _search_text(query)
    normalized_candidate = _search_text(candidate)
    if not normalized_query or not normalized_candidate:
        return 0.0
    if normalized_query == normalized_candidate:
        return 1.0
    if normalized_candidate.startswith(normalized_query):
        return 0.98
    if normalized_query in normalized_candidate:
        return 0.95

    score = SequenceMatcher(None, normalized_query, normalized_candidate).ratio()
    if " " not in normalized_query:
        score = max(
            score,
            *(
                SequenceMatcher(None, normalized_query, token).ratio()
                for token in normalized_candidate.split()
            ),
        )
    return score


def _best_fuzzy_score(query: str, values: list[str | None]) -> float:
    return max((_fuzzy_score(query, value) for value in values), default=0.0)


def _recipe_search_score(
    query: str,
    recipe: dict[str, Any],
    tags: list[str],
    ingredients: list[str],
) -> float:
    if not query:
        return 0.0

    title_score = _fuzzy_score(query, recipe["title"])
    tag_score = _best_fuzzy_score(query, tags) * 0.82
    ingredient_score = _best_fuzzy_score(query, ingredients) * 0.68
    metadata_score = _best_fuzzy_score(
        query,
        [
            recipe.get("slug"),
            recipe.get("source_name"),
            recipe.get("source_url"),
            recipe.get("author"),
            recipe.get("imported_from"),
        ],
    ) * 0.5
    return max(title_score, tag_score, ingredient_score, metadata_score)
