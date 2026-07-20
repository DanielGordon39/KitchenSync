from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path
from pprint import pprint
from typing import TYPE_CHECKING
from urllib.parse import urlparse

import yt_dlp

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


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    if __package__:
        from .recipe_text_parser import parse_recipe_text
    else:
        from recipe_text_parser import parse_recipe_text

    args = build_parser().parse_args()
    urls = read_urls(args.url_file)
    if not urls:
        raise SystemExit(f"No recipe URLs found in {args.url_file}")

    for index, url in enumerate(urls, start=1):
        print("\n" + "=" * 100)
        print(f"Recipe {index}/{len(urls)} [{identify_platform(url)}]")
        print(url)
        print("=" * 100)

        try:
            source_info = acquire_source(url)
        except Exception as error:
            print(f"\nSource acquisition failed: {error}")
            continue

        print_recipe_evidence(source_info)

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
