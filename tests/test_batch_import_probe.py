import importlib.util
import sys
from pathlib import Path

from kitchensync.models import Ingredient, Recipe, RecipeIngredient, RecipeMetadata
from kitchensync.parsing import ParseResult, ParseStatus


def test_batch_import_probe_saves_successes_and_writes_reports(
    tmp_path,
    monkeypatch,
    capsys,
):
    probe = _load_probe_module()
    url_file = tmp_path / "urls.txt"
    url_file.write_text(
        "\n".join(
            [
                "# ignored comment",
                "https://example.com/tomato-soup",
                "",
                "https://example.com/broken",
            ]
        ),
        encoding="utf-8",
    )

    def fake_parse_recipe(url):
        if url.endswith("/broken"):
            return ParseResult(
                status=ParseStatus.FAILED,
                source=url,
                message="stubbed failure",
            )

        return ParseResult(
            recipe=Recipe(
                name="Tomato Soup",
                metadata=RecipeMetadata(source_url=url, source_name="Example"),
                ingredients=[
                    RecipeIngredient(
                        ingredient=Ingredient(name="Roma Tomato"),
                        notes=["raw: 6 Roma tomatoes"],
                    )
                ],
            ),
            status=ParseStatus.SUCCESS,
            source=url,
        )

    monkeypatch.setattr(probe, "parse_recipe", fake_parse_recipe)

    rows = probe.run_batch_import(
        url_file,
        database_path=tmp_path / "library" / "kitchensync.sqlite",
        report_dir=tmp_path / "reports",
    )

    captured = capsys.readouterr()

    assert [row.status for row in rows] == ["success", "failed"]
    assert rows[0].saved is True
    assert rows[0].title == "Tomato Soup"
    assert rows[1].saved is False
    assert "Tomato Soup" in captured.out
    assert (
        tmp_path / "library" / "recipes" / "tomato-soup" / "recipe.md"
    ).exists()
    assert (tmp_path / "reports" / "import_report.csv").exists()
    assert (tmp_path / "reports" / "import_report.jsonl").exists()
    assert "stubbed failure" in (
        tmp_path / "reports" / "import_report.md"
    ).read_text(encoding="utf-8")


def test_batch_import_probe_can_write_supported_sites(tmp_path):
    probe = _load_probe_module()

    path = probe.write_supported_sites(tmp_path)
    text = path.read_text(encoding="utf-8")

    assert "recipe-scrapers supported hosts" in text
    assert "allrecipes.com" in text
    assert "hellofresh.com" in text


def _load_probe_module():
    probe_path = Path(__file__).parents[1] / "scratch" / "batch_import_probe.py"
    spec = importlib.util.spec_from_file_location("batch_import_probe", probe_path)
    assert spec is not None
    assert spec.loader is not None

    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module
