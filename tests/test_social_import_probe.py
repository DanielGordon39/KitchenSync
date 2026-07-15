import importlib.util
import sys
from pathlib import Path


def test_social_import_probe_reads_urls_and_identifies_youtube_shorts(tmp_path):
    probe = _load_probe_module()
    url_file = tmp_path / "social_urls.txt"
    url_file.write_text(
        "\n".join(
            [
                "# ignored comment",
                "https://www.youtube.com/shorts/example-id",
                "",
                "https://www.instagram.com/reel/example-id/",
            ]
        ),
        encoding="utf-8",
    )

    rows = probe.build_probe_rows(probe.read_urls(url_file))

    assert [(row.platform, row.status) for row in rows] == [
        ("youtube_shorts", "planned"),
        ("instagram", "planned"),
    ]


def _load_probe_module():
    probe_path = Path(__file__).parents[1] / "scratch" / "social_import_probe.py"
    spec = importlib.util.spec_from_file_location("social_import_probe", probe_path)
    assert spec is not None
    assert spec.loader is not None

    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module
