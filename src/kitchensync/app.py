from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any


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


class KitchenSyncApp:
    def __init__(self, connection: sqlite3.Connection):
        self.connection = connection
        self.recipes = RecipesAPI(connection)
        self.cookbook = CookbookAPI(connection)

    @classmethod
    def open(cls, database_path: str | Path = DEFAULT_DATABASE_PATH) -> KitchenSyncApp:
        connection = _connect(Path(database_path))
        connection.executescript(SCHEMA_SQL)
        connection.commit()
        return cls(connection)

    def close(self) -> None:
        self.connection.close()

    def __enter__(self) -> KitchenSyncApp:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()


class RecipesAPI:
    def __init__(self, connection: sqlite3.Connection):
        self.connection = connection

    def save_metadata(
        self,
        *,
        recipe_id: str,
        title: str,
        slug: str | None = None,
        servings: int | None = None,
        source_name: str | None = None,
        source_url: str | None = None,
        markdown_path: str | None = None,
    ) -> None:
        self.connection.execute(
            """
            INSERT INTO recipe_recipes (
                recipe_id, title, slug, servings, source_name, source_url, markdown_path
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(recipe_id) DO UPDATE SET
                title = excluded.title,
                slug = excluded.slug,
                servings = excluded.servings,
                source_name = excluded.source_name,
                source_url = excluded.source_url,
                markdown_path = excluded.markdown_path,
                updated_at = CURRENT_TIMESTAMP
            """,
            (recipe_id, title, slug, servings, source_name, source_url, markdown_path),
        )
        self.connection.execute(
            """
            INSERT INTO recipe_search (recipe_id, search_text)
            VALUES (?, ?)
            ON CONFLICT(recipe_id) DO UPDATE SET search_text = excluded.search_text
            """,
            (
                recipe_id,
                " ".join(
                    value
                    for value in (title, slug, source_name, source_url)
                    if value is not None
                ),
            ),
        )
        self.connection.commit()

    def get(self, recipe_id: str) -> dict[str, Any] | None:
        row = self.connection.execute(
            "SELECT * FROM recipe_recipes WHERE recipe_id = ?",
            (recipe_id,),
        ).fetchone()
        return _row_dict(row)

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
