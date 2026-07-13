from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any
from uuid import uuid4

from .markdown import (
    ingredient_to_markdown,
    raw_ingredient_text,
    recipe_to_markdown,
    slugify,
)
from .models import Ingredient, Recipe


DEFAULT_DATABASE_PATH = Path("data/library/kitchensync.sqlite")


SCHEMA_SQL = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS recipe_recipes (
    recipe_id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    slug TEXT,
    servings INTEGER,
    source_name TEXT,
    source_url TEXT,
    author TEXT,
    imported_from TEXT,
    time_estimate_minutes INTEGER,
    markdown_path TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS recipe_ingredients (
    recipe_id TEXT NOT NULL REFERENCES recipe_recipes(recipe_id) ON DELETE CASCADE,
    ingredient_order INTEGER NOT NULL,
    raw_text TEXT NOT NULL,
    ingredient_id TEXT,
    parsed_name TEXT,
    quantity_amount REAL,
    quantity_unit TEXT,
    preparation TEXT,
    PRIMARY KEY (recipe_id, ingredient_order)
);

CREATE TABLE IF NOT EXISTS recipe_steps (
    recipe_id TEXT NOT NULL REFERENCES recipe_recipes(recipe_id) ON DELETE CASCADE,
    step_order INTEGER NOT NULL,
    text TEXT NOT NULL,
    PRIMARY KEY (recipe_id, step_order)
);

CREATE TABLE IF NOT EXISTS recipe_search (
    recipe_id TEXT PRIMARY KEY REFERENCES recipe_recipes(recipe_id) ON DELETE CASCADE,
    search_text TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS recipe_tags (
    recipe_id TEXT NOT NULL REFERENCES recipe_recipes(recipe_id) ON DELETE CASCADE,
    tag_order INTEGER NOT NULL,
    tag_slug TEXT NOT NULL,
    PRIMARY KEY (recipe_id, tag_order)
);

CREATE TABLE IF NOT EXISTS ingredient_ingredients (
    ingredient_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    slug TEXT,
    parent_ingredient_id TEXT REFERENCES ingredient_ingredients(ingredient_id),
    category TEXT,
    storage_area TEXT,
    default_unit TEXT
);

CREATE TABLE IF NOT EXISTS ingredient_aliases (
    ingredient_id TEXT NOT NULL REFERENCES ingredient_ingredients(ingredient_id) ON DELETE CASCADE,
    alias TEXT NOT NULL,
    PRIMARY KEY (ingredient_id, alias)
);

CREATE TABLE IF NOT EXISTS ingredient_packaging (
    ingredient_id TEXT NOT NULL REFERENCES ingredient_ingredients(ingredient_id) ON DELETE CASCADE,
    package_id TEXT NOT NULL,
    name TEXT NOT NULL,
    quantity REAL,
    unit TEXT,
    store_unit TEXT,
    notes TEXT,
    PRIMARY KEY (ingredient_id, package_id)
);

CREATE TABLE IF NOT EXISTS ingredient_conversions (
    ingredient_id TEXT NOT NULL REFERENCES ingredient_ingredients(ingredient_id) ON DELETE CASCADE,
    conversion_id TEXT NOT NULL,
    from_quantity REAL NOT NULL,
    from_unit TEXT NOT NULL,
    to_quantity REAL NOT NULL,
    to_unit TEXT NOT NULL,
    preparation TEXT,
    confidence TEXT,
    PRIMARY KEY (ingredient_id, conversion_id)
);

CREATE TABLE IF NOT EXISTS cookbook_entries (
    recipe_id TEXT PRIMARY KEY REFERENCES recipe_recipes(recipe_id) ON DELETE CASCADE,
    recipe_slug TEXT,
    title TEXT NOT NULL,
    recipe_path TEXT,
    cookbook_path TEXT NOT NULL,
    favorite INTEGER NOT NULL DEFAULT 0,
    rating INTEGER,
    status TEXT NOT NULL DEFAULT 'active',
    notes TEXT,
    last_cooked_on TEXT,
    indexed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS cookbook_cook_events (
    cook_event_id INTEGER PRIMARY KEY AUTOINCREMENT,
    recipe_id TEXT NOT NULL REFERENCES cookbook_entries(recipe_id) ON DELETE CASCADE,
    cooked_on TEXT NOT NULL,
    notes TEXT
);

CREATE TABLE IF NOT EXISTS pantry_items (
    ingredient_id TEXT PRIMARY KEY,
    amount REAL,
    unit TEXT,
    notes TEXT,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS shopping_lists (
    shopping_list_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'active',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS shopping_items (
    shopping_item_id INTEGER PRIMARY KEY AUTOINCREMENT,
    shopping_list_id TEXT NOT NULL REFERENCES shopping_lists(shopping_list_id) ON DELETE CASCADE,
    ingredient_id TEXT,
    label TEXT NOT NULL,
    amount REAL,
    unit TEXT,
    checked INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS candidate_candidates (
    candidate_id TEXT PRIMARY KEY,
    candidate_type TEXT NOT NULL CHECK (candidate_type IN ('recipe', 'ingredient')),
    status TEXT NOT NULL DEFAULT 'pending_review',
    source TEXT,
    payload_json TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    resolved_at TEXT
);

CREATE TABLE IF NOT EXISTS candidate_events (
    candidate_event_id INTEGER PRIMARY KEY AUTOINCREMENT,
    candidate_id TEXT NOT NULL REFERENCES candidate_candidates(candidate_id) ON DELETE CASCADE,
    action TEXT NOT NULL,
    notes TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""


RECIPE_RECIPE_COLUMNS = {
    "author": "TEXT",
    "imported_from": "TEXT",
    "time_estimate_minutes": "INTEGER",
}


def _connect(database_path: Path) -> sqlite3.Connection:
    database_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(database_path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def _row_dict(row: sqlite3.Row | None) -> dict[str, Any] | None:
    return dict(row) if row is not None else None


def _rows(rows: list[sqlite3.Row]) -> list[dict[str, Any]]:
    return [dict(row) for row in rows]


def _time_estimate_minutes(recipe: Recipe) -> int | None:
    if recipe.time_estimate is None:
        return None

    return recipe.time_estimate.base_minutes


def _migrate_schema(connection: sqlite3.Connection) -> None:
    recipe_columns = {
        row["name"]
        for row in connection.execute("PRAGMA table_info(recipe_recipes)").fetchall()
    }
    for column_name, column_type in RECIPE_RECIPE_COLUMNS.items():
        if column_name not in recipe_columns:
            connection.execute(
                f"ALTER TABLE recipe_recipes ADD COLUMN {column_name} {column_type}"
            )


class KitchenSyncApp:
    def __init__(self, connection: sqlite3.Connection, database_path: Path):
        self.connection = connection
        self.database_path = database_path
        self.library_root = database_path.parent
        self.recipes = RecipesAPI(connection, self.library_root)
        self.ingredients = IngredientsAPI(connection)
        self.cookbook = CookbookAPI(connection)

    @classmethod
    def open(cls, database_path: str | Path = DEFAULT_DATABASE_PATH) -> KitchenSyncApp:
        database_path = Path(database_path)
        connection = _connect(database_path)
        connection.executescript(SCHEMA_SQL)
        _migrate_schema(connection)
        connection.commit()
        return cls(connection, database_path)

    def close(self) -> None:
        self.connection.close()

    def __enter__(self) -> KitchenSyncApp:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()


class RecipesAPI:
    def __init__(self, connection: sqlite3.Connection, library_root: Path):
        self.connection = connection
        self.library_root = library_root

    def save_imported_recipe(self, recipe: Recipe) -> None:
        slug = slugify(recipe.name)
        recipe_id = self._recipe_id_for_import(recipe, slug)

        self._write_recipe_file(recipe, slug)
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
            markdown_path=f"recipes/{slug}.md",
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
            markdown_path=markdown_path,
        )
        self._upsert_recipe_search(
            recipe_id,
            [title, slug, source_name, source_url, author, imported_from],
        )
        self.connection.commit()

    def _write_recipe_file(self, recipe: Recipe, slug: str) -> None:
        recipe_path = self.library_root / "recipes" / f"{slug}.md"
        recipe_path.parent.mkdir(parents=True, exist_ok=True)
        recipe_path.write_text(recipe_to_markdown(recipe), encoding="utf-8")

    def _ensure_ingredient_files_and_rows(self, recipe: Recipe) -> None:
        ingredient_dir = self.library_root / "ingredients"
        ingredient_dir.mkdir(parents=True, exist_ok=True)

        seen_slugs: set[str] = set()
        for item in recipe.ingredients:
            slug = slugify(item.ingredient.name)
            if slug in seen_slugs:
                continue
            seen_slugs.add(slug)

            ingredient_id = self._ingredient_id_for_slug(slug)
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

    def _ingredient_id_for_slug(self, slug: str) -> str:
        row = self.connection.execute(
            """
            SELECT ingredient_id
            FROM ingredient_ingredients
            WHERE slug = ?
            LIMIT 1
            """,
            (slug,),
        ).fetchone()
        if row is not None:
            return row["ingredient_id"]

        return uuid4().hex

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
                markdown_path
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(recipe_id) DO UPDATE SET
                title = excluded.title,
                slug = excluded.slug,
                servings = excluded.servings,
                source_name = excluded.source_name,
                source_url = excluded.source_url,
                author = excluded.author,
                imported_from = excluded.imported_from,
                time_estimate_minutes = excluded.time_estimate_minutes,
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
            ingredient_slug = slugify(item.ingredient.name)
            ingredient_id = self._ingredient_id_for_slug(ingredient_slug)

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

    def list(self) -> list[dict[str, Any]]:
        rows = self.connection.execute(
            """
            SELECT *
            FROM recipe_recipes
            ORDER BY lower(title)
            """
        ).fetchall()
        return [self._recipe_row(row) for row in rows if row is not None]

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

        return {
            "recipe": recipe,
            "ingredients": _rows(ingredients),
            "steps": _rows(steps),
        }

    def search(self, query: str) -> list[dict[str, Any]]:
        pattern = f"%{query.casefold()}%"
        rows = self.connection.execute(
            """
            SELECT r.*
            FROM recipe_recipes AS r
            LEFT JOIN recipe_search AS s ON s.recipe_id = r.recipe_id
            WHERE lower(r.title) LIKE ? OR lower(coalesce(s.search_text, '')) LIKE ?
            ORDER BY lower(r.title)
            """,
            (pattern, pattern),
        ).fetchall()
        return [self._recipe_row(row) for row in rows if row is not None]

    def _recipe_row(self, row: sqlite3.Row | None) -> dict[str, Any] | None:
        recipe = _row_dict(row)
        if recipe is None:
            return None

        recipe["tags"] = self._recipe_tags(recipe["recipe_id"])
        return recipe

    def _recipe_tags(self, recipe_id: str) -> list[str]:
        rows = self.connection.execute(
            """
            SELECT tag_slug
            FROM recipe_tags
            WHERE recipe_id = ?
            ORDER BY tag_order
            """,
            (recipe_id,),
        ).fetchall()
        return [row["tag_slug"] for row in rows]


class IngredientsAPI:
    def __init__(self, connection: sqlite3.Connection):
        self.connection = connection

    def list(self) -> list[dict[str, Any]]:
        rows = self.connection.execute(
            """
            SELECT
                ingredient_id,
                name,
                slug,
                parent_ingredient_id,
                category,
                storage_area,
                default_unit
            FROM ingredient_ingredients
            ORDER BY lower(name)
            """
        ).fetchall()
        return _rows(rows)


class CookbookAPI:
    def __init__(self, connection: sqlite3.Connection):
        self.connection = connection

    def index_entry(
        self,
        *,
        recipe_id: str,
        title: str,
        cookbook_path: str,
        recipe_slug: str | None = None,
        recipe_path: str | None = None,
        favorite: bool = False,
        rating: int | None = None,
        status: str = "active",
        notes: str | None = None,
        last_cooked_on: str | None = None,
    ) -> None:
        if rating is not None and not 1 <= rating <= 5:
            raise ValueError("rating must be between 1 and 5")

        self.connection.execute(
            """
            INSERT INTO cookbook_entries (
                recipe_id,
                recipe_slug,
                title,
                recipe_path,
                cookbook_path,
                favorite,
                rating,
                status,
                notes,
                last_cooked_on
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(recipe_id) DO UPDATE SET
                recipe_slug = excluded.recipe_slug,
                title = excluded.title,
                recipe_path = excluded.recipe_path,
                cookbook_path = excluded.cookbook_path,
                favorite = excluded.favorite,
                rating = excluded.rating,
                status = excluded.status,
                notes = excluded.notes,
                last_cooked_on = excluded.last_cooked_on,
                indexed_at = CURRENT_TIMESTAMP
            """,
            (
                recipe_id,
                recipe_slug,
                title,
                recipe_path,
                cookbook_path,
                1 if favorite else 0,
                rating,
                status,
                notes,
                last_cooked_on,
            ),
        )
        self.connection.commit()

    def list_entries(self) -> list[dict[str, Any]]:
        rows = self.connection.execute(
            """
            SELECT
                c.recipe_id,
                c.recipe_slug,
                c.title,
                c.recipe_path,
                c.cookbook_path,
                r.servings,
                r.source_name,
                r.source_url,
                c.favorite,
                c.rating,
                c.status,
                c.notes,
                c.last_cooked_on,
                c.indexed_at
            FROM cookbook_entries AS c
            JOIN recipe_recipes AS r ON r.recipe_id = c.recipe_id
            ORDER BY lower(c.title)
            """
        ).fetchall()
        return _rows(rows)
