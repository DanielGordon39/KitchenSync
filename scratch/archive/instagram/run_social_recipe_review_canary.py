from __future__ import annotations

import argparse
import base64
import json
import sqlite3
from pathlib import Path

from kitchensync import KitchenSyncApp
from kitchensync import recipe_api, web
from kitchensync.parsing import acquire_instagram_source, parse_recipe_text


CASE_DIR = Path(__file__).parent / "social_recipe_cases"
DEFAULT_DATABASE_PATH = (
    Path(__file__).parent
    / "social_import_probe_output"
    / "review_flow_canary_final_20260722"
    / "kitchensync.sqlite"
)
REAL_DATABASE_PATH = Path(__file__).parents[1] / "data" / "library" / "kitchensync.sqlite"
CASE_FILES = {
    14: "014-korean-spicy-tofu-stew-meal-prep.json",
    28: "028-coriander-garlic-and-butter-prawns-and-clam.json",
    44: "044-kansas-city-style-bbq-chicken-bites-and-crispy-potatoes.json",
    75: "075-high-protein-mee-goreng.json",
    97: "097-cinnamon-roll-cheesecake-protein-bites.json",
}
TINY_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate reviewed social-recipe canaries in a disposable library."
    )
    parser.add_argument("--database-path", type=Path, default=DEFAULT_DATABASE_PATH)
    parser.add_argument(
        "--live",
        action="store_true",
        help="Acquire current Instagram descriptions and thumbnails instead of using deterministic stubs.",
    )
    parser.add_argument(
        "--serve",
        action="store_true",
        help="Serve an existing disposable canary library on port 8000 for UI review.",
    )
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    database_path = args.database_path.resolve()
    if args.serve:
        if not database_path.exists():
            raise SystemExit(f"Canary database does not exist: {database_path}")
        _serve_canary(database_path, args.port)
        return 0
    if database_path.exists():
        raise SystemExit(f"Refusing to reuse existing canary database: {database_path}")

    _use_disposable_database(database_path)
    existing_ingredients = _copy_existing_catalog(database_path)
    if not args.live:
        recipe_api._fetch_image = lambda _uri: (TINY_PNG, "image/png")

    reports = []
    for index, filename in CASE_FILES.items():
        case = json.loads((CASE_DIR / filename).read_text(encoding="utf-8"))
        source = acquire_instagram_source(case["source_url"]) if args.live else None
        source_text = source.description if source else case["source_text"]
        if not source_text:
            raise RuntimeError(f"case {index} has no description")
        result = parse_recipe_text(source_text)
        if result.candidate is None or result.fallback_recommended:
            raise RuntimeError(f"case {index} no longer produces a complete candidate")
        if result.candidate.model_dump(
            include={"name", "servings", "raw_ingredients", "steps", "tags"}
        ) != case["expected"]:
            raise RuntimeError(f"case {index} no longer matches the frozen corpus")

        draft, corrections = _reviewed_draft(index, result.candidate)
        detail = web.save_recipe_import(
            web.RecipeImportRequest(
                draft=draft,
                source_url=source.source_url if source else case["source_url"],
                source_name=source.source_name if source else "Instagram",
                author=source.author if source else case.get("creator"),
                thumbnail_url=(
                    source.thumbnail_url
                    if source
                    else f"https://canary.local/{index}.png"
                ),
                duplicate_action="import",
            )
        )
        reports.append(
            {
                "case": index,
                "title": detail.recipe.title,
                "recipe_id": detail.recipe.recipe_id,
                "image_url": detail.recipe.image_url,
                "corrections": corrections,
            }
        )

    cards = web.list_recipes()
    with KitchenSyncApp.open(database_path) as app:
        ingredients = app.ingredients.list()
        details = [app.recipes.get_detail(card.recipe_id) for card in cards]

    library_root = database_path.parent
    markdown_files = sorted(library_root.glob("recipes/*/recipe.md"))
    image_files = sorted(library_root.glob("recipes/*/images/main.*"))
    if len(cards) != 5 or len(details) != 5:
        raise RuntimeError("the disposable library does not contain five recipe details")
    if len(markdown_files) != 5 or len(image_files) != 5:
        raise RuntimeError("the disposable library does not contain five Markdown/image pairs")
    if any(not path.read_bytes() for path in image_files):
        raise RuntimeError("a canary image is empty")

    print(json.dumps(reports, ensure_ascii=False, indent=2))
    print()
    print(f"database: {database_path}")
    print(f"recipe cards: {len(cards)}")
    print(f"recipe details: {len(details)}")
    print(f"recipe Markdown files: {len(markdown_files)}")
    print(f"local images: {len(image_files)}")
    print(f"ingredient catalog entries: {len(ingredients)}")
    print(
        "new canonical ingredients: "
        + ", ".join(
            sorted(
                ingredient["name"]
                for ingredient in ingredients
                if ingredient["name"].casefold() not in existing_ingredients
            )
        )
    )
    return 0


def _reviewed_draft(index: int, candidate) -> tuple[web.RecipeUpdateRequest, list[str]]:
    title = candidate.name
    ingredients = list(candidate.raw_ingredients)
    steps = list(candidate.steps)
    corrections: list[str] = []

    if index == 28:
        title = "Coriander, Garlic & Butter Prawns & Clams"
        _replace(ingredients, "250g @allthingsdairy__ butter", "250 g Butter")
        _replace(
            ingredients,
            "1 stick of bruised lemongrass",
            "1 stick lemongrass, bruised",
        )
        _replace(ingredients, "Spring onions", "Green Onions")
        corrections.extend(
            [
                "Normalized the title and pluralized Clams.",
                "Changed '250g @allthingsdairy__ butter' to existing Butter.",
                "Separated Lemongrass from the 'bruised' preparation.",
                "Matched Spring Onions to existing Green Onions.",
            ]
        )
    elif index == 44:
        _replace(
            ingredients,
            "2 lbs (1 kg) lotatoes/Carisma potatoes low-carb potatoes, cut into small pieces",
            "2 lbs (1 kg) Carisma potatoes, cut into small pieces",
        )
        _replace(
            ingredients,
            "⅓ cup (70 g) replacement brown sugar (monk fruit)",
            "⅓ cup (70 g) Brown Sugar Substitute, monk-fruit based",
        )
        corrections.extend(
            [
                "Removed the 'lotatoes' source typo before canonical save.",
                "Normalized replacement brown sugar to Brown Sugar Substitute.",
            ]
        )
    elif index == 75:
        title = "High-Protein Mee Goreng"
        _replace_many(
            ingredients,
            "400g chicken breast / tenders cubed + 1 tbsp oyster sauce + 1 tsp dark soy sauce",
            [
                "400 g chicken breast or tenders, cubed",
                "1 tbsp oyster sauce",
                "1 tsp dark soy sauce",
            ],
        )
        _replace(ingredients, "250g raw prawns", "250 g Prawns, raw")
        _replace(ingredients, "4 spring onions chopped", "4 Green Onions, chopped")
        _replace_many(
            ingredients,
            "To serve: Chili oil, crispy shallots, lime wedges.",
            [
                "Chili oil, to serve",
                "Crispy shallots, to serve",
                "Lime, cut into wedges, to serve",
            ],
        )
        _replace(
            steps,
            "Divide between bowls and top with a drizzle of chilli oil, crispy shallots and a squeeze of fresh lim",
            "Divide between bowls and top with a drizzle of chilli oil, crispy shallots and a squeeze of fresh lime.",
        )
        corrections.extend(
            [
                "Normalized the all-caps title.",
                "Split the chicken, oyster sauce, and dark soy sauce source line.",
                "Split the three serving garnishes.",
                "Matched Raw Prawns, Spring Onions, and Lime to reviewed canonical names.",
                "Completed the truncated final step from 'fresh lim' to 'fresh lime'.",
            ]
        )
    elif index == 97:
        _replace(
            ingredients,
            "2 tbsp light cream cheese, softened",
            "2 tbsp Cream Cheese, light and softened",
        )
        _replace(ingredients, "1 tsp melted butter", "1 tsp Butter, melted")
        _replace_many(
            ingredients,
            "Optional: 1 tablespoon of cane sugar, and 1 teaspoon of cinnamon for coating.",
            [
                "1 tbsp Sugar, optional for coating",
                "1 tsp ground cinnamon, optional, for coating",
            ],
        )
        corrections.extend(
            [
                "Matched Light Cream Cheese and melted Butter to existing canonical ingredients.",
                "Split the optional coating and matched Cane Sugar to existing Sugar.",
            ]
        )
    else:
        corrections.append("No recipe-field corrections were needed.")

    return (
        web.RecipeUpdateRequest(
            title=title,
            description=candidate.description,
            servings=candidate.servings,
            time_estimate_minutes=None,
            tags=candidate.tags,
            ingredients=ingredients,
            steps=steps,
            notes=candidate.notes,
        ),
        corrections,
    )


def _replace(values: list[str], old: str, new: str) -> None:
    index = values.index(old)
    values[index] = new


def _replace_many(values: list[str], old: str, replacements: list[str]) -> None:
    index = values.index(old)
    values[index : index + 1] = replacements


def _use_disposable_database(database_path: Path) -> None:
    class DisposableKitchenSyncApp:
        @staticmethod
        def open():
            return KitchenSyncApp.open(database_path)

    web.KitchenSyncApp = DisposableKitchenSyncApp


def _copy_existing_catalog(database_path: Path) -> set[str]:
    source = sqlite3.connect(
        f"file:{REAL_DATABASE_PATH.resolve().as_posix()}?mode=ro", uri=True
    )
    source.row_factory = sqlite3.Row
    try:
        ingredients = source.execute(
            "SELECT ingredient_id, name, slug, category, storage_area, default_unit "
            "FROM ingredient_ingredients"
        ).fetchall()
        aliases = source.execute(
            "SELECT ingredient_id, alias FROM ingredient_aliases"
        ).fetchall()
    finally:
        source.close()

    with KitchenSyncApp.open(database_path) as app:
        app.connection.executemany(
            """
            INSERT INTO ingredient_ingredients
                (ingredient_id, name, slug, category, storage_area, default_unit)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            [tuple(row) for row in ingredients],
        )
        app.connection.executemany(
            "INSERT INTO ingredient_aliases (ingredient_id, alias) VALUES (?, ?)",
            [tuple(row) for row in aliases],
        )
        app.connection.commit()
    return {row["name"].casefold() for row in ingredients}


def _serve_canary(database_path: Path, port: int) -> None:
    import uvicorn
    from fastapi.staticfiles import StaticFiles

    _use_disposable_database(database_path)
    web.app.routes[:] = [
        route for route in web.app.routes if getattr(route, "name", None) != "library"
    ]
    web.app.mount(
        "/library",
        StaticFiles(directory=database_path.parent),
        name="library",
    )
    uvicorn.run(web.app, host="127.0.0.1", port=port)


if __name__ == "__main__":
    raise SystemExit(main())
