import re
from urllib.request import Request, urlopen

from kitchensync.models import (
    Ingredient,
    Recipe,
    RecipeIngredient,
    RecipeMetadata,
    RecipeStep,
)

from .result import ParseResult, ParseStatus


def _fetch_html(url: str) -> str:
    request = Request(
        url,
        headers={"User-Agent": "KitchenSync/0.1 recipe parser"},
    )

    with urlopen(request, timeout=10) as response:
        charset = response.headers.get_content_charset() or "utf-8"
        return response.read().decode(charset, errors="replace")


def _try(func, default=None):
    try:
        return func()
    except Exception:
        return default


def _instructions_from_scraper(scraper) -> list[str]:
    lines = _try(scraper.instructions_list, default=None)
    if lines:
        return [line.strip() for line in lines if line.strip()]

    text = _try(scraper.instructions, default="")
    return [line.strip() for line in text.splitlines() if line.strip()]


def _parse_servings(value: object) -> int | None:
    if not isinstance(value, str):
        return None

    match = re.search(r"\d+", value)
    return int(match.group()) if match else None


def _recipe_from_scraper(scraper, source_url: str) -> Recipe:
    ingredients = [
        # TODO: Normalize raw ingredient lines into quantity/unit/name/preparation.
        RecipeIngredient(ingredient=Ingredient(name=line))
        for line in scraper.ingredients()
        if line.strip()
    ]

    instruction_lines = _instructions_from_scraper(scraper)
    steps = [
        RecipeStep(order=index, text=text)
        for index, text in enumerate(instruction_lines, start=1)
    ]

    return Recipe(
        name=scraper.title(),
        servings=_parse_servings(_try(scraper.yields)),
        ingredients=ingredients,
        steps=steps,
        metadata=RecipeMetadata(
            description=_try(scraper.description),
            author=_try(scraper.author),
            source_name=_try(scraper.site_name),
            source_url=source_url,
            imported_from="recipe-scrapers",
        ),
    )


def parse_recipe_url(url: str) -> ParseResult:
    # TODO: Prefer a well-supported recipe parsing library first; replace with a local parser if it falls short.
    # TODO: If recipe-scrapers is too high-level, evaluate extruct as a lower-level metadata fallback.
    # TODO: Add site-specific parsers only after generic parsing fails for a site we use repeatedly.
    # TODO: First known site-parser target: https://moribyan.com/chipotle-chicken-copycat/
    try:
        from recipe_scrapers import scrape_html

        html = _fetch_html(url)
        scraper = scrape_html(html, org_url=url)
        recipe = _recipe_from_scraper(scraper, source_url=url)
    except Exception as exc:
        return ParseResult(
            status=ParseStatus.FAILED,
            source=url,
            message=f"Could not parse recipe page: {exc}",
        )

    return ParseResult(status=ParseStatus.SUCCESS, source=url, recipe=recipe)
