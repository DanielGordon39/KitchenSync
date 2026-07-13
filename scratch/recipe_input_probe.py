import argparse
import sys
from pathlib import Path

from kitchensync.app import DEFAULT_DATABASE_PATH, KitchenSyncApp
from kitchensync.markdown import recipe_to_markdown, write_recipe_markdown_files
from kitchensync.parsing import parse_recipe


DEFAULT_RECIPE_URL = (
    "https://www.hellofresh.com/recipes/"
    "blackened-chicken-penne-61b0d03ab3a03377ee6b1b04"
)
DEFAULT_OUTPUT_DIR = Path(__file__).parent / "recipe_input_probe_output"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Parse a recipe URL and write probe Markdown output."
    )
    parser.add_argument("url", nargs="?", default=DEFAULT_RECIPE_URL)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Directory for generated recipe and ingredient Markdown files.",
    )
    parser.add_argument(
        "--save-to-library",
        action="store_true",
        help="Also save the parsed recipe through KitchenSyncApp.",
    )
    parser.add_argument(
        "--database-path",
        type=Path,
        default=DEFAULT_DATABASE_PATH,
        help="SQLite database path to use with --save-to-library.",
    )
    return parser


def run_probe(
    url: str,
    *,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    save_to_library: bool = False,
    database_path: Path = DEFAULT_DATABASE_PATH,
) -> None:
    result = parse_recipe(url)

    print("status:", result.status.value)
    print("source:", result.source)
    print("message:", result.message)

    if not result.recipe:
        return

    print()
    print(recipe_to_markdown(result.recipe))

    paths = write_recipe_markdown_files(result.recipe, output_dir)
    print("wrote markdown files:")
    for path in paths:
        print(f"- {path}")

    if save_to_library:
        with KitchenSyncApp.open(database_path) as app:
            app.recipes.save_imported_recipe(result.recipe)

        print("saved to library:")
        print(f"- database: {database_path}")
        print(f"- root: {database_path.parent}")


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    args = build_parser().parse_args()
    run_probe(
        args.url,
        output_dir=args.output_dir,
        save_to_library=args.save_to_library,
        database_path=args.database_path,
    )


if __name__ == "__main__":
    main()
