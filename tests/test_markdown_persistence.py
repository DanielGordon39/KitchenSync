from kitchensync.markdown import (
    ingredient_to_markdown,
    recipe_to_markdown,
    slugify,
    write_recipe_markdown_files,
)
from kitchensync.models import (
    Ingredient,
    Quantity,
    Recipe,
    RecipeIngredient,
    RecipeMetadata,
    RecipeStep,
)


def test_recipe_to_markdown_uses_readable_facts_without_frontmatter():
    recipe = Recipe(
        name="Blackened Chicken Penne",
        servings=2,
        metadata=RecipeMetadata(
            description="Creamy pasta.",
            source_name="HelloFresh",
            source_url="https://example.com/recipe",
            author="Michelle Doll Olson",
            imported_from="recipe-scrapers",
        ),
        ingredients=[
            RecipeIngredient(
                ingredient=Ingredient(name="Chicken Breast"),
                quantity=Quantity(amount=10, unit="ounce"),
                notes=["raw: 10 ounce Chicken Breast Strips"],
            )
        ],
        steps=[RecipeStep(order=1, text="Pat chicken dry. • Season all over.")],
        notes=["Reduce spice for kids."],
    )

    markdown = recipe_to_markdown(recipe)

    assert markdown.startswith("# Blackened Chicken Penne\n")
    assert "---" not in markdown
    assert "schema_version:" not in markdown
    assert "id:" not in markdown
    assert "- Author: Michelle Doll Olson" in markdown
    assert "- Imported from: recipe-scrapers" in markdown
    assert "- 10 ounce Chicken Breast Strips" in markdown
    assert "- Pat chicken dry." in markdown
    assert "- Season all over." in markdown
    assert "## Notes" in markdown


def test_ingredient_to_markdown_uses_heading_and_aliases():
    markdown = ingredient_to_markdown(
        Ingredient(name="Chicken Breast", aliases=["chicken breast strips"]),
    )

    assert markdown.startswith("# Chicken Breast\n")
    assert "---" not in markdown
    assert "schema_version:" not in markdown
    assert "- chicken breast strips" in markdown
    assert "Source recipe lines" not in markdown


def test_write_recipe_markdown_files_writes_recipe_and_ingredient_stubs(tmp_path):
    recipe = Recipe(
        name="Tomato Soup",
        ingredients=[
            RecipeIngredient(
                ingredient=Ingredient(name="Roma Tomato"),
                quantity=Quantity(amount=2, unit="unit"),
            )
        ],
    )

    paths = write_recipe_markdown_files(recipe, tmp_path)

    assert paths == [
        tmp_path / "recipes" / "tomato-soup.md",
        tmp_path / "ingredients" / "roma-tomato.md",
    ]
    recipe_text = (tmp_path / "recipes" / "tomato-soup.md").read_text(
        encoding="utf-8"
    )
    assert recipe_text.startswith("# Tomato Soup\n")
    assert "# Roma Tomato" in (
        tmp_path / "ingredients" / "roma-tomato.md"
    ).read_text(encoding="utf-8")


def test_slugify_keeps_filename_identity_simple():
    assert slugify("  Blackened Chicken Penne!  ") == "blackened-chicken-penne"
    assert slugify("!!!") == "untitled"
