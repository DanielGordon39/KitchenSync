# Scratch

Tracked exploratory scripts for KitchenSync data-import experiments.

Current tools:

- `recipe_urls.txt`: newline-separated recipe URLs for local batch import testing.
- `batch_import_probe.py`: parses URLs, optionally saves successful recipes to `data/library`, and writes summary reports under `scratch/batch_import_probe_output/`.

Scratch scripts are not production entrypoints. They may call live URLs and write local ignored probe output.
