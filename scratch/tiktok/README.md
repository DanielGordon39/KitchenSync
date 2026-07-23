# TikTok Scratch

TikTok-specific research stays here until acquisition and parsing behavior are understood well enough for a separate production promotion.

Current files:

- `tiktok_recipe_urls.txt`: discovery target and later frozen URL queue.
- `tiktok-recipe-parser-loop-plan.md`: source discovery, acquisition, production-parser evaluation, scratch-only experiment rules, and Goal Mode handoff.

Artifacts created only during the loop:

- `tiktok_recipe_cases/`: frozen descriptions and reviewed expectations.
- `tiktok_recipe_acquisition_failures.json`: failed or unsupported acquisition outcomes.
- `run_tiktok_recipe_corpus.py`: offline regression runner after the first usable case exists.
- `tiktok-recipe-parser-results.md`: completion report consumed by the Facebook–TikTok comparison.

Reuse `scratch/social_import_probe.py` with the TikTok queue path. Do not create a TikTok parser or acquisition wrapper until observed evidence demonstrates that the shared probe or production parser is insufficient.
