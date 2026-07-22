# Scratch

Tracked exploratory scripts for KitchenSync social-import experiments.

Current tools:

- `social_recipe_urls.txt`: newline-separated social-media recipe URLs for the current research corpus.
- `social_import_probe.py`: owns URL-corpus loading, platform identification, `yt-dlp` evidence acquisition, and readable probe output.
- `recipe_text_parser.py`: keeps compatibility imports for the production parser in `src/kitchensync/parsing/social.py`.
- `run_social_recipe_review_canary.py`: validates reviewed cases against a disposable library, with optional live Instagram acquisition.

Responsibility flow:

```text
social URL
  -> social_import_probe.py acquires source evidence
  -> description, caption, or transcript text
  -> kitchensync.parsing.social returns a candidate and diagnostics
  -> later orchestration may request fallback extraction
  -> explicit review before any accepted save
```

The production text parser does not fetch social URLs, persist recipes, or directly own an LLM provider. The probe may eventually choose a fallback when the deterministic parser recommends one.

The repeatable website recipe importer now lives at `scripts/import_recipe_urls.py`.

Scratch scripts are not production entrypoints or durable model contracts. They may call live URLs and will eventually write local ignored probe output under `scratch/social_import_probe_output/`.
