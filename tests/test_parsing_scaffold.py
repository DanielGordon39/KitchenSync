from kitchensync.parsing import ParseResult, ParseStatus, parse_recipe
from kitchensync.parsing import recipe as recipe_parser


def test_parse_recipe_imports_from_public_parsing_package():
    assert callable(parse_recipe)


def test_parse_recipe_routes_urls_to_web_parser(monkeypatch):
    def fake_parse_recipe_url(url):
        return ParseResult(
            status=ParseStatus.NOT_IMPLEMENTED,
            source=url,
            message="fake web parser",
        )

    monkeypatch.setattr(recipe_parser, "parse_recipe_url", fake_parse_recipe_url)

    result = parse_recipe("https://example.com/recipe")

    assert result.status == ParseStatus.NOT_IMPLEMENTED
    assert result.source == "https://example.com/recipe"
    assert result.recipe is None
    assert result.message == "fake web parser"


def test_parse_recipe_routes_pdfs_to_pdf_placeholder():
    result = parse_recipe("recipe.pdf")

    assert result.status == ParseStatus.NOT_IMPLEMENTED
    assert result.source == "recipe.pdf"
    assert result.recipe is None
    assert "PDF recipe parsing" in result.message


def test_parse_recipe_routes_images_to_image_placeholder():
    result = parse_recipe("recipe.jpg")

    assert result.status == ParseStatus.NOT_IMPLEMENTED
    assert result.source == "recipe.jpg"
    assert result.recipe is None
    assert "Image recipe parsing" in result.message


def test_parse_recipe_rejects_unknown_sources():
    result = parse_recipe("recipe.txt")

    assert result.status == ParseStatus.UNSUPPORTED_SOURCE
    assert result.source == "recipe.txt"
    assert result.recipe is None
