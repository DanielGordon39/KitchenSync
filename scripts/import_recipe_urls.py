from __future__ import annotations

import argparse
import csv
import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

from kitchensync.app import DEFAULT_DATABASE_PATH, KitchenSyncApp
from kitchensync.markdown import slugify
from kitchensync.parsing import ParseStatus, parse_recipe


DEFAULT_URL_FILE = Path(__file__).parent / "recipe_urls.txt"
DEFAULT_REPORT_DIR = Path("data/imports/web_recipe_reports")


@dataclass
class ImportReportRow:
    index: int
    url: str
    status: str
    saved: bool
    already_in_database: bool
    recipe_id: str | None = None
    title: str | None = None
    slug: str | None = None
    servings: int | None = None
    ingredient_count: int | None = None
    step_count: int | None = None
    tags: str | None = None
    time_estimate_minutes: int | None = None
    source_name: str | None = None
    author: str | None = None
    message: str | None = None


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Batch parse recipe URLs and optionally save them to KitchenSync."
    )
    parser.add_argument(
        "url_file",
        nargs="?",
        type=Path,
        default=DEFAULT_URL_FILE,
        help="Text file with one recipe URL per line.",
    )
    parser.add_argument(
        "--database-path",
        type=Path,
        default=DEFAULT_DATABASE_PATH,
        help="SQLite database path used when saving recipes.",
    )
    parser.add_argument(
        "--report-dir",
        type=Path,
        default=DEFAULT_REPORT_DIR,
        help="Directory for CSV, JSONL, and Markdown import reports.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Maximum number of URLs to process.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Parse and report without writing recipes to the library.",
    )
    parser.add_argument(
        "--stop-on-error",
        action="store_true",
        help="Stop after the first failed parse or save.",
    )
    parser.add_argument(
        "--list-supported-sites",
        action="store_true",
        help="Write recipe-scrapers supported hosts to the report directory.",
    )
    return parser


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    args = build_parser().parse_args()
    if args.list_supported_sites:
        supported_path = write_supported_sites(args.report_dir)
        print(f"wrote supported sites: {supported_path}")
        return

    rows = run_batch_import(
        args.url_file,
        database_path=args.database_path,
        report_dir=args.report_dir,
        limit=args.limit,
        dry_run=args.dry_run,
        stop_on_error=args.stop_on_error,
    )
    print_summary(rows, args.report_dir)


def run_batch_import(
    url_file: Path = DEFAULT_URL_FILE,
    *,
    database_path: Path = DEFAULT_DATABASE_PATH,
    report_dir: Path = DEFAULT_REPORT_DIR,
    limit: int | None = None,
    dry_run: bool = False,
    stop_on_error: bool = False,
) -> list[ImportReportRow]:
    urls = read_urls(url_file)
    if limit is not None:
        urls = urls[:limit]

    report_dir.mkdir(parents=True, exist_ok=True)
    rows: list[ImportReportRow] = []

    with KitchenSyncApp.open(database_path) as app:
        for index, url in enumerate(urls, start=1):
            row = import_one_url(
                app,
                index=index,
                url=url,
                dry_run=dry_run,
            )
            rows.append(row)
            print_progress(row)

            if stop_on_error and row.status != ParseStatus.SUCCESS.value:
                break

    write_reports(rows, report_dir)
    return rows


def import_one_url(
    app: KitchenSyncApp,
    *,
    index: int,
    url: str,
    dry_run: bool,
) -> ImportReportRow:
    try:
        result = parse_recipe(url)
    except Exception as exc:
        return ImportReportRow(
            index=index,
            url=url,
            status="exception",
            saved=False,
            already_in_database=False,
            message=str(exc),
        )

    if result.recipe is None:
        return ImportReportRow(
            index=index,
            url=url,
            status=result.status.value,
            saved=False,
            already_in_database=False,
            message=result.message,
        )

    recipe = result.recipe
    slug = slugify(recipe.name)
    existing_recipe_id = find_existing_recipe_id(app, url, slug)

    saved = False
    recipe_id = existing_recipe_id
    message = result.message
    if result.status == ParseStatus.SUCCESS and not dry_run:
        try:
            app.recipes.save_imported_recipe(recipe)
        except Exception as exc:
            return ImportReportRow(
                index=index,
                url=url,
                status="save_failed",
                saved=False,
                already_in_database=existing_recipe_id is not None,
                recipe_id=existing_recipe_id,
                title=recipe.name,
                slug=slug,
                servings=recipe.servings,
                ingredient_count=len(recipe.ingredients),
                step_count=len(recipe.steps),
                tags=", ".join(recipe.tags) if recipe.tags else None,
                time_estimate_minutes=(
                    recipe.time_estimate.base_minutes if recipe.time_estimate else None
                ),
                source_name=recipe.metadata.source_name,
                author=recipe.metadata.author,
                message=str(exc),
            )
        else:
            recipe_id = find_existing_recipe_id(app, url, slug)
            saved = True

    return ImportReportRow(
        index=index,
        url=url,
        status=result.status.value,
        saved=saved,
        already_in_database=existing_recipe_id is not None,
        recipe_id=recipe_id,
        title=recipe.name,
        slug=slug,
        servings=recipe.servings,
        ingredient_count=len(recipe.ingredients),
        step_count=len(recipe.steps),
        tags=", ".join(recipe.tags) if recipe.tags else None,
        time_estimate_minutes=(
            recipe.time_estimate.base_minutes if recipe.time_estimate else None
        ),
        source_name=recipe.metadata.source_name,
        author=recipe.metadata.author,
        message=message,
    )


def read_urls(path: Path) -> list[str]:
    urls = []
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        urls.append(stripped)
    return urls


def find_existing_recipe_id(
    app: KitchenSyncApp,
    source_url: str,
    slug: str,
) -> str | None:
    row = app.connection.execute(
        """
        SELECT recipe_id
        FROM recipe_recipes
        WHERE source_url = ?
        ORDER BY created_at
        LIMIT 1
        """,
        (source_url,),
    ).fetchone()
    if row is not None:
        return row["recipe_id"]

    row = app.connection.execute(
        """
        SELECT recipe_id
        FROM recipe_recipes
        WHERE slug = ?
        ORDER BY created_at
        LIMIT 1
        """,
        (slug,),
    ).fetchone()
    return row["recipe_id"] if row is not None else None


def write_reports(rows: list[ImportReportRow], report_dir: Path) -> None:
    write_csv_report(rows, report_dir / "import_report.csv")
    write_jsonl_report(rows, report_dir / "import_report.jsonl")
    write_markdown_report(rows, report_dir / "import_report.md")


def write_csv_report(rows: list[ImportReportRow], path: Path) -> None:
    fieldnames = list(ImportReportRow.__dataclass_fields__)
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(asdict(row))


def write_jsonl_report(rows: list[ImportReportRow], path: Path) -> None:
    with path.open("w", encoding="utf-8") as file:
        for row in rows:
            file.write(json.dumps(asdict(row), ensure_ascii=False) + "\n")


def write_markdown_report(rows: list[ImportReportRow], path: Path) -> None:
    lines = [
        "# Batch Import Report",
        "",
        f"- URLs processed: {len(rows)}",
        f"- Successful parses: {sum(row.status == ParseStatus.SUCCESS.value for row in rows)}",
        f"- Saved recipes: {sum(row.saved for row in rows)}",
        f"- Already in database: {sum(row.already_in_database for row in rows)}",
        "",
        "| # | Status | Saved | Existing | Title | URL | Message |",
        "|---:|---|---:|---:|---|---|---|",
    ]
    for row in rows:
        lines.append(
            "| "
            + " | ".join(
                [
                    str(row.index),
                    _markdown_cell(row.status),
                    "yes" if row.saved else "no",
                    "yes" if row.already_in_database else "no",
                    _markdown_cell(row.title),
                    _markdown_cell(row.url),
                    _markdown_cell(row.message),
                ]
            )
            + " |"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_supported_sites(report_dir: Path = DEFAULT_REPORT_DIR) -> Path:
    from recipe_scrapers import SCRAPERS

    report_dir.mkdir(parents=True, exist_ok=True)
    path = report_dir / "recipe_scrapers_supported_sites.txt"
    hosts = sorted(SCRAPERS)
    lines = [
        "# recipe-scrapers supported hosts",
        f"# Count: {len(hosts)}",
        "# Generated from the installed recipe-scrapers package.",
        "",
        *hosts,
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def print_progress(row: ImportReportRow) -> None:
    title = row.title or row.message or row.url
    saved = "saved" if row.saved else "not saved"
    existing = "existing" if row.already_in_database else "new"
    print(f"[{row.index}] {row.status} / {saved} / {existing}: {title}")


def print_summary(rows: Iterable[ImportReportRow], report_dir: Path) -> None:
    rows = list(rows)
    print()
    print("batch import summary")
    print(f"- processed: {len(rows)}")
    print(f"- successful parses: {sum(row.status == ParseStatus.SUCCESS.value for row in rows)}")
    print(f"- saved: {sum(row.saved for row in rows)}")
    print(f"- already in database: {sum(row.already_in_database for row in rows)}")
    print(f"- reports: {report_dir}")


def _markdown_cell(value: object) -> str:
    if value is None:
        return ""

    return str(value).replace("|", "\\|").replace("\n", " ")


if __name__ == "__main__":
    main()
