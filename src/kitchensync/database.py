"""SQLite schema, connection setup, and small row-conversion helpers."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any


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
    main_image_path TEXT,
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
    "main_image_path": "TEXT",
}


def connect(database_path: Path) -> sqlite3.Connection:
    database_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(database_path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def row_dict(row: sqlite3.Row | None) -> dict[str, Any] | None:
    return dict(row) if row is not None else None


def rows(database_rows: list[sqlite3.Row]) -> list[dict[str, Any]]:
    return [dict(row) for row in database_rows]


def migrate_schema(connection: sqlite3.Connection) -> None:
    recipe_columns = {
        row["name"]
        for row in connection.execute("PRAGMA table_info(recipe_recipes)").fetchall()
    }
    for column_name, column_type in RECIPE_RECIPE_COLUMNS.items():
        if column_name not in recipe_columns:
            connection.execute(
                f"ALTER TABLE recipe_recipes ADD COLUMN {column_name} {column_type}"
            )
