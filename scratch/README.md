# Scratch

Tracked exploratory scripts for KitchenSync social-import experiments.

Current tools:

- `social_recipe_urls.txt`: newline-separated social-media recipe URLs for the current research corpus.
- `social_import_probe.py`: reads the corpus, identifies the likely platform, and exposes explicit placeholders for evidence acquisition, transcription fallback, review-candidate extraction, and later platform comparison.

The repeatable website recipe importer now lives at `scripts/import_recipe_urls.py`.

Scratch scripts are not production entrypoints or durable model contracts. They may call live URLs and will eventually write local ignored probe output under `scratch/social_import_probe_output/`.
