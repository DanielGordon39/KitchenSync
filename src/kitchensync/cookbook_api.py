from __future__ import annotations

import sqlite3
from typing import Any

from .database import rows


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
        entry_rows = self.connection.execute(
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
        return rows(entry_rows)
