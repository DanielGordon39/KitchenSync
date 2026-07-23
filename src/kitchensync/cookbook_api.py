"""Cookbook relationship state synchronized between Markdown and SQLite."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

from .database import rows


class CookbookAPI:
    """Manage one local Cookbook without duplicating recipe content."""

    def __init__(self, connection: sqlite3.Connection, library_root: Path):
        self.connection = connection
        self.library_root = library_root

    def save_entry(
        self,
        recipe_id: str,
        *,
        favorite: bool = False,
        rating: int | None = None,
        notes: str | None = None,
    ) -> dict[str, Any] | None:
        """Write durable Cookbook metadata and refresh its index row."""

        if rating is not None and not 1 <= rating <= 5:
            raise ValueError("rating must be between 1 and 5")

        recipe = self.connection.execute(
            "SELECT * FROM recipe_recipes WHERE recipe_id = ?",
            (recipe_id,),
        ).fetchone()
        if recipe is None:
            return None

        existing = self.get_entry(recipe_id)
        cookbook_path = (
            existing["cookbook_path"]
            if existing
            else f"cookbook/{recipe['slug'] or recipe_id}.md"
        )
        status = existing["status"] if existing else "active"
        last_cooked_on = existing["last_cooked_on"] if existing else None

        path = self.library_root / cookbook_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            _entry_markdown(
                title=recipe["title"],
                recipe_path=recipe["markdown_path"],
                favorite=favorite,
                rating=rating,
                status=status,
                notes=notes,
                last_cooked_on=last_cooked_on,
            ),
            encoding="utf-8",
        )
        self.index_entry(
            recipe_id=recipe_id,
            recipe_slug=recipe["slug"],
            title=recipe["title"],
            recipe_path=recipe["markdown_path"],
            cookbook_path=cookbook_path,
            favorite=favorite,
            rating=rating,
            status=status,
            notes=notes,
            last_cooked_on=last_cooked_on,
        )
        return self.get_entry(recipe_id)

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
        """Update the rebuildable index for an existing Cookbook entry."""

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
        """List Cookbook entries joined to current recipe metadata."""

        entry_rows = self.connection.execute(
            """
            SELECT
                c.recipe_id,
                r.slug AS recipe_slug,
                r.title,
                r.markdown_path AS recipe_path,
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

    def get_entry(self, recipe_id: str) -> dict[str, Any] | None:
        """Return Cookbook metadata for one canonical recipe."""

        row = self.connection.execute(
            """
            SELECT
                c.recipe_id,
                r.slug AS recipe_slug,
                r.title,
                r.markdown_path AS recipe_path,
                c.cookbook_path,
                c.favorite,
                c.rating,
                c.status,
                c.notes,
                c.last_cooked_on,
                c.indexed_at
            FROM cookbook_entries AS c
            JOIN recipe_recipes AS r ON r.recipe_id = c.recipe_id
            WHERE c.recipe_id = ?
            """,
            (recipe_id,),
        ).fetchone()
        return dict(row) if row is not None else None


def _entry_markdown(
    *,
    title: str,
    recipe_path: str | None,
    favorite: bool,
    rating: int | None,
    status: str,
    notes: str | None,
    last_cooked_on: str | None,
) -> str:
    lines = [
        f"# {title}",
        "",
        f"- Recipe: {recipe_path or ''}",
        f"- Favorite: {'yes' if favorite else 'no'}",
        f"- Rating: {rating or ''}",
        f"- Status: {status}",
    ]
    if last_cooked_on:
        lines.append(f"- Last cooked: {last_cooked_on}")
    if notes and notes.strip():
        lines.extend(["", "## Notes", "", notes.strip()])
    return "\n".join(lines).strip() + "\n"
