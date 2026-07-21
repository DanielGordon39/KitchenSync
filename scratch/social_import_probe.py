from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from pprint import pprint
from typing import TYPE_CHECKING
from urllib.parse import urlparse

import yt_dlp

from kitchensync.app import KitchenSyncApp
from kitchensync.markdown import slugify
from kitchensync.models import (
    ImageRef,
    Ingredient,
    Recipe,
    RecipeIngredient,
    RecipeMetadata,
    RecipeStep,
)
from kitchensync.parsing import parse_recipe_ingredient_line

if TYPE_CHECKING:
    from recipe_text_parser import RecipeTextParseResult, SocialRecipeCandidate


DEFAULT_URL_FILE = Path(__file__).parent / "social_recipe_urls.txt"
CASE_DIR = Path(__file__).parent / "social_recipe_cases"
DEFAULT_PROMOTION_DATABASE = (
    Path(__file__).parent
    / "social_import_probe_output"
    / "data"
    / "library"
    / "kitchensync.sqlite"
)
SCORED_FIELDS = {"name", "servings", "raw_ingredients", "steps", "tags"}


@dataclass
class SocialProbeRow:
    index: int
    url: str
    platform: str
    status: str = "planned"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Plan the next social-recipe import probe for a URL corpus."
    )
    parser.add_argument(
        "url_file",
        nargs="?",
        type=Path,
        default=DEFAULT_URL_FILE,
        help="Text file with one social-media recipe URL per line.",
    )
    parser.add_argument(
        "--index",
        type=int,
        help="Process one 1-based queue entry instead of the complete file.",
    )
    parser.add_argument(
        "--acquire-only",
        action="store_true",
        help="Print source evidence without running the text parser.",
    )
    parser.add_argument(
        "--promote",
        nargs="+",
        type=int,
        metavar="INDEX",
        help="Reparse selected accepted, complete frozen corpus cases.",
    )
    parser.add_argument(
        "--database-path",
        type=Path,
        default=DEFAULT_PROMOTION_DATABASE,
        help="Disposable SQLite path used by --promote --save.",
    )
    parser.add_argument(
        "--save",
        action="store_true",
        help="Save promoted cases through app.recipes.save_imported_recipe(...).",
    )
    return parser


def print_recipe_evidence(source_info: dict[str, object]) -> None:
    preview = {
        "recipe_fields_to_extract": {
            "name": "from description",
            "servings": "from description",
            "ingredients": "from bulleted description section",
            "steps": "from numbered description section",
            "tags": "from hashtags",
            "time_estimate": None,
        },
        "metadata_candidates": {
            "author": source_info.get("uploader"),
            "source_name": source_info.get("extractor"),
            "source_url": (
                source_info.get("webpage_url")
                or source_info.get("original_url")
            ),
            "imported_from": "yt-dlp",
            "main_image_uri": source_info.get("thumbnail"),
        },
        "evidence": {
            "has_description": bool(source_info.get("description")),
            "has_captions": bool(
                source_info.get("subtitles")
                or source_info.get("automatic_captions")
            ),
        },
    }

    pprint(preview, sort_dicts=False, width=100)

    print("\nRaw description evidence:\n")
    print(source_info.get("description") or "(no description)")


def print_parse_result(result: RecipeTextParseResult) -> None:
    print("\nPer-line recipe evidence:\n")
    for line in result.line_analyses:
        evidence = " ".join(
            f"{concept}={strength:.1f}"
            for concept, strength in line.evidence.items()
        ) or "unclassified"
        print(f"{line.line_number:>2} | {evidence:<38} | {line.text}")

    print("\nContextual Recipe field candidates:\n")
    for candidate in result.field_candidates:
        fields = " ".join(
            f"{field}={score:.1f}"
            for field, score in sorted(
                candidate.field_scores.items(),
                key=lambda item: item[1],
                reverse=True,
            )
        )
        start = candidate.line_numbers[0]
        stop = candidate.line_numbers[-1]
        line_range = str(start) if start == stop else f"{start}-{stop}"
        print(f"{fields} | lines {line_range}")
        for line_number, text in zip(candidate.line_numbers, candidate.lines):
            print(f"  {line_number:>2} | {text}")
        print()

    print("\nRecipe text parser summary:\n")
    pprint(
        result.model_dump(exclude={"candidate", "line_analyses", "field_candidates"}),
        sort_dicts=False,
        width=100,
    )


def build_recipe_preview(
    candidate: SocialRecipeCandidate | None,
    source_info: dict[str, object],
) -> Recipe | None:
    if candidate is None or not candidate.name:
        return None

    ingredients = []
    for raw_ingredient in candidate.raw_ingredients:
        try:
            ingredient = parse_recipe_ingredient_line(raw_ingredient)
        except Exception:
            ingredient = RecipeIngredient(
                ingredient=Ingredient(name=raw_ingredient),
                notes=[f"raw: {raw_ingredient}"],
            )
        ingredients.append(ingredient)

    thumbnail = source_info.get("thumbnail")
    images = [ImageRef(uri=thumbnail)] if isinstance(thumbnail, str) and thumbnail else []
    source_url = source_info.get("webpage_url") or source_info.get("original_url")

    return Recipe(
        name=candidate.name,
        servings=candidate.servings,
        ingredients=ingredients,
        steps=[
            RecipeStep(order=order, text=text)
            for order, text in enumerate(candidate.steps, start=1)
        ],
        tags=candidate.tags,
        notes=candidate.notes,
        metadata=RecipeMetadata(
            description=candidate.description,
            source_name=_optional_text(source_info.get("extractor")),
            source_url=_optional_text(source_url),
            author=_optional_text(source_info.get("uploader")),
            imported_from="yt-dlp",
            images=images,
        ),
    )


def _optional_text(value: object) -> str | None:
    return value if isinstance(value, str) and value else None


def print_recipe_preview(
    recipe: Recipe | None,
    result: RecipeTextParseResult,
) -> None:
    print("\nRecipe model preview:\n")
    if recipe is None:
        print("(no Recipe preview: a name is required)")
    else:
        pprint(recipe.model_dump(), sort_dicts=False, width=120)

    print("\nReview status:")
    print("ready for review" if not result.fallback_recommended else "incomplete")
    for warning in result.warnings:
        print(f"- {warning}")


def load_frozen_cases(indices: list[int]) -> list[dict[str, object]]:
    cases_by_index = {}
    for path in CASE_DIR.glob("*.json"):
        case = json.loads(path.read_text(encoding="utf-8"))
        cases_by_index[case["queue_index"]] = case

    missing = [index for index in indices if index not in cases_by_index]
    if missing:
        raise ValueError(f"No frozen case for queue index: {', '.join(map(str, missing))}")
    if len(indices) != len(set(indices)):
        raise ValueError("Promotion indices must be unique")
    return [cases_by_index[index] for index in indices]


def promotion_source_info(case: dict[str, object]) -> dict[str, object]:
    source_info = {
        "description": case["source_text"],
        "extractor": "Instagram",
        "uploader": case.get("creator"),
        "webpage_url": case["source_url"],
    }
    try:
        live_info = acquire_source(str(case["source_url"]))
    except Exception as error:
        print(f"Live metadata refresh failed; continuing without an image: {error}")
        return source_info

    for field in ("extractor", "thumbnail", "uploader"):
        if live_info.get(field):
            source_info[field] = live_info[field]
    return source_info


def promote_frozen_cases(
    indices: list[int],
    *,
    database_path: Path,
    save: bool,
    parse_recipe_text,
) -> int:
    cases = load_frozen_cases(indices)
    failures = 0
    app = KitchenSyncApp.open(database_path) if save else None

    try:
        for case in cases:
            index = case["queue_index"]
            print("\n" + "=" * 100)
            print(f"Frozen case {index}: {case['source_url']}")
            print("=" * 100)

            try:
                if not case.get("accepted") or not case.get("expected_complete"):
                    raise ValueError("only accepted complete cases may be promoted")

                result = parse_recipe_text(str(case["source_text"]))
                if result.candidate is None or result.fallback_recommended:
                    raise ValueError("the current parser no longer produces a complete candidate")

                actual = result.candidate.model_dump(include=SCORED_FIELDS)
                if actual != case["expected"]:
                    raise ValueError("the current parser no longer matches the frozen oracle")

                source_info = promotion_source_info(case)
                recipe = build_recipe_preview(result.candidate, source_info)
                if recipe is None:
                    raise ValueError("the candidate could not be converted to a Recipe")

                print(
                    f"ready: {recipe.name} / {len(recipe.ingredients)} ingredients / "
                    f"{len(recipe.steps)} steps / image candidate: "
                    f"{'yes' if recipe.metadata.images else 'no'}"
                )
                if app is not None:
                    app.recipes.save_imported_recipe(recipe)
                    saved = app.recipes.get_by_slug(slugify(recipe.name))
                    print(
                        "saved: "
                        + str(database_path)
                        + " / image: "
                        + (str(saved.get("main_image_path")) if saved else "none")
                    )
            except Exception as error:
                failures += 1
                print(f"promotion failed: {error}")
    finally:
        if app is not None:
            app.close()

    print("\npromotion summary")
    print(f"- selected: {len(cases)}")
    print(f"- successful: {len(cases) - failures}")
    print(f"- saved: {len(cases) - failures if save else 0}")
    print(f"- database: {database_path if save else '(dry run)'}")
    return failures


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    if __package__:
        from .recipe_text_parser import parse_recipe_text
    else:
        from recipe_text_parser import parse_recipe_text

    parser = build_parser()
    args = parser.parse_args()
    if args.save and not args.promote:
        parser.error("--save requires --promote")
    if args.promote:
        if args.index is not None or args.acquire_only:
            parser.error("--promote cannot be combined with --index or --acquire-only")
        failures = promote_frozen_cases(
            args.promote,
            database_path=args.database_path,
            save=args.save,
            parse_recipe_text=parse_recipe_text,
        )
        raise SystemExit(1 if failures else 0)

    urls = read_urls(args.url_file)
    if not urls:
        raise SystemExit(f"No recipe URLs found in {args.url_file}")

    indexed_urls = list(enumerate(urls, start=1))
    if args.index is not None:
        if not 1 <= args.index <= len(urls):
            raise SystemExit(f"--index must be between 1 and {len(urls)}")
        indexed_urls = [indexed_urls[args.index - 1]]

    for index, url in indexed_urls:
        print("\n" + "=" * 100)
        print(f"Queue entry {index}/{len(urls)} [{identify_platform(url)}]")
        print(url)
        print("=" * 100)

        try:
            source_info = acquire_source(url)
        except Exception as error:
            print(f"\nSource acquisition failed: {error}")
            continue

        print_recipe_evidence(source_info)

        if args.acquire_only:
            continue

        description = source_info.get("description")
        if not isinstance(description, str) or not description.strip():
            print("\nNo description text is available for recipe parsing.")
            continue

        parse_result = parse_recipe_text(description)
        print_parse_result(parse_result)
        recipe_preview = build_recipe_preview(parse_result.candidate, source_info)
        print_recipe_preview(recipe_preview, parse_result)


def read_urls(path: Path) -> list[str]:
    urls = []
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        urls.append(stripped)
    return urls


def acquire_source(url: str) -> dict[str, object]:
    with yt_dlp.YoutubeDL({}) as ydl:
        info = ydl.extract_info(url, download=False)
        return ydl.sanitize_info(info)


def identify_platform(url: str) -> str:
    parsed = urlparse(url)
    host = parsed.netloc.casefold().removeprefix("www.")
    path = parsed.path.casefold()

    if host in {"youtube.com", "m.youtube.com"}:
        return "youtube_shorts" if path.startswith("/shorts/") else "youtube"
    if host == "youtu.be":
        return "youtube"
    if host in {"instagram.com", "m.instagram.com"}:
        return "instagram"
    if host in {"tiktok.com", "m.tiktok.com", "vm.tiktok.com"}:
        return "tiktok"
    if host in {"facebook.com", "m.facebook.com", "fb.watch"}:
        return "facebook"
    return "unsupported"


def build_probe_rows(urls: list[str]) -> list[SocialProbeRow]:
    return [
        SocialProbeRow(index=index, url=url, platform=identify_platform(url))
        for index, url in enumerate(urls, start=1)
    ]


def print_probe_plan(rows: list[SocialProbeRow]) -> None:
    for row in rows:
        print(f"[{row.index}] {row.platform} / {row.status}: {row.url}")

    print()
    print("next probe boundaries")
    print("- acquire description, source metadata, captions, and image candidates")
    print("- transcribe downloaded audio only when usable captions are unavailable")
    print("- build a reviewable recipe candidate without saving it")
    print("- compare YouTube results with later TikTok, Instagram, and Facebook URLs")


# TODO(step 5): Prefer existing captions, then evaluate local faster-whisper transcription.
# TODO(step 6): Implement recipe text parsing one stage at a time in recipe_text_parser.py.
# TODO(step 7): Add a UI workflow for user-supplied printable recipe URLs;
# never automate comments or creator-profile navigation.
# TODO(step 8): Add observed TikTok, Instagram, and Facebook URLs one platform at a time.


if __name__ == "__main__":
    main()
