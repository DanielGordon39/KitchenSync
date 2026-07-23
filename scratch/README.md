# Scratch

Tracked exploratory scripts for active KitchenSync social-import experiments.

Active platform passes:

- `facebook_recipe_urls.txt`: frozen feasibility queue of discovered public Facebook sources.
- `facebook-recipe-parser-loop-plan.md`: evidence-first loop and stop conditions.
- `tiktok/`: TikTok discovery queue, feasibility plan, and platform-specific scratch artifacts.
- `facebook-tiktok-comparison-plan.md`: comparison and production-promotion gate to run only after both platform passes finish.
- `social_import_probe.py`: URL loading, platform identification, `yt-dlp` evidence acquisition, and readable production-parser diagnostics.
- `recipe_text_parser.py`: compatibility imports for the production parser in `src/kitchensync/parsing/social/`.

Responsibility flow:

```text
social URL
  -> social_import_probe.py acquires source evidence
  -> description or caption text
  -> kitchensync.parsing.social returns a candidate and diagnostics
  -> freeze and label evidence before considering an experiment
```

The production text parser does not fetch social URLs, persist recipes, or directly own an LLM provider. These passes do not save recipes or edit production parsing code.

The repeatable website recipe importer now lives at `scripts/import_recipe_urls.py`.

Completed work is retained under `scratch/archive/`. The frozen Instagram corpus remains regression evidence even though its plans and runners are archived.

Scratch scripts are not production entrypoints or durable model contracts. They may call live URLs and write local ignored probe output under `scratch/social_import_probe_output/`.
