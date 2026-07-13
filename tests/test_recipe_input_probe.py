import importlib.util
from pathlib import Path

from kitchensync.models import Ingredient, Recipe, RecipeIngredient
from kitchensync.parsing.result import ParseResult, ParseStatus


def test_recipe_input_probe_can_save_to_library(tmp_path, monkeypatch, capsys):
    probe = _load_probe_module()
    recipe = Recipe(
        name="Tomato Soup",
        ingredients=[
            RecipeIngredient(
                ingredient=Ingredient(name="Roma Tomato"),
                notes=["raw: 6 Roma tomatoes"],
            )
        ],
    )

    monkeypatch.setattr(
        probe,
        "parse_recipe",
        lambda url: ParseResult(
            recipe=recipe,
            status=ParseStatus.SUCCESS,
            source=url,
            message="stubbed",
        ),
    )

    probe.run_probe(
        "https://example.com/tomato-soup",
        output_dir=tmp_path / "probe-output",
        save_to_library=True,
        database_path=tmp_path / "library" / "kitchensync.sqlite",
    )

    captured = capsys.readouterr()

    assert (tmp_path / "probe-output" / "recipes" / "tomato-soup.md").exists()
    assert (tmp_path / "library" / "recipes" / "tomato-soup.md").exists()
    assert (tmp_path / "library" / "ingredients" / "roma-tomato.md").exists()
    assert "saved to library:" in captured.out


def _load_probe_module():
    probe_path = Path(__file__).parents[1] / "scratch" / "recipe_input_probe.py"
    spec = importlib.util.spec_from_file_location("recipe_input_probe", probe_path)
    assert spec is not None
    assert spec.loader is not None

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
