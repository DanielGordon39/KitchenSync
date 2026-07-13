import argparse
import sys
from pathlib import Path

from kitchensync.markdown import recipe_to_markdown, write_recipe_markdown_files
from kitchensync.parsing import parse_recipe


DEFAULT_RECIPE_URL = (
    "https://www.hellofresh.com/recipes/"
    "blackened-chicken-penne-61b0d03ab3a03377ee6b1b04"
)
DEFAULT_OUTPUT_DIR = Path(__file__).parent / "recipe_input_probe_output"


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

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
    args = parser.parse_args()

    result = parse_recipe(args.url)

    print("status:", result.status.value)
    print("source:", result.source)
    print("message:", result.message)

    if not result.recipe:
        return

    print()
    print(recipe_to_markdown(result.recipe))

    paths = write_recipe_markdown_files(result.recipe, args.output_dir)
    print("wrote markdown files:")
    for path in paths:
        print(f"- {path}")


if __name__ == "__main__":
    main()
