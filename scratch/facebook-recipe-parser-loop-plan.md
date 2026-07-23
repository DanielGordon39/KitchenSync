# Facebook Recipe Parsing Loop Plan

Status: preparation complete; live acquisition and parsing have not started.

## Goal

Evaluate whether public Facebook recipe video posts can reuse KitchenSync's
existing acquisition probe and production social-text parser. Preserve the
Instagram evidence, keep all experiments under `scratch/`, and make no
production edits during this pass.

The loop is:

```text
public Facebook URL
  -> acquire source evidence with the existing yt-dlp probe
  -> freeze the exact acquired description and minimal metadata
  -> label expected fields from source evidence
  -> run kitchensync.parsing.parse_recipe_text unchanged
  -> accept, record fallback, or classify the smallest failure
  -> add scratch-only experimental code only for a repeated parser failure
  -> rerun every Facebook case and the archived Instagram regression corpus
```

## Preparation state

- The completed Instagram work is under `scratch/archive/instagram/`.
- Its 96 frozen cases remain regression evidence: 57 complete and 39 fallback
  cases were exact at the completion gate.
- `scratch/facebook_recipe_urls.txt` contains 12 links preserved exactly as
  discovered: nine public video posts and three public text-post controls.
- The indexed Facebook pages exposed recipe-like descriptions during
  discovery, but search excerpts are not frozen corpus evidence.
- Live local acquisition was not completed while preparing this plan because
  the current execution environment could not authorize outbound access.

Do not infer an acquisition or parser result from discovery excerpts. The first
live run starts at queue entry 1.

## Authority and boundaries

Allowed:

- Read production models and parser APIs.
- Call `kitchensync.parsing.parse_recipe_text` unchanged.
- Edit tracked plans, queues, cases, and experimental helpers under `scratch/`.
- Run the archived Instagram corpus, focused checks, and `uv run pytest`.
- Read public Facebook pages and acquire public metadata without interacting
  with the account or downloading media.

Not allowed:

- Do not edit `src/`, `ui/`, runtime configuration, dependencies, or production
  tests to change behavior.
- Do not save imported recipes.
- Do not add an LLM, transcription, browser-automation, or scraping framework.
- Do not like, comment, follow, share, message, or change Facebook account
  state.
- Do not replace failed URLs after the queue is frozen.

Tests may be updated only when a scratch file move changes a fixture path; they
must not define new Facebook behavior in this pass.

## Start gate

Before attempting the first URL:

1. Read `AGENTS.md`, the required `.agents/` policies, this plan, and the
   archived Instagram expansion results.
2. Run the archived Instagram corpus with the production parser:

   ```text
   uv run python scratch/archive/instagram/run_social_recipe_corpus.py
   ```

3. Run `uv run pytest`.
4. Capture `git status --short` and preserve unrelated work.
5. Confirm the environment can access public Facebook pages through the
   installed `yt-dlp` extractor. Login-required failures are acquisition
   results; do not add credentials to the repository.

## Frozen queue

Process every uncommented URL in `scratch/facebook_recipe_urls.txt` in order.
Do not rewrite, canonicalize, shorten, deduplicate, or silently replace a URL.

The queue deliberately includes:

- Nine `/videos/` URLs with indexed recipe descriptions from several pages.
- Three `/posts/` URLs as text-post acquisition controls.

The controls answer whether the existing acquisition boundary can obtain
non-video post text. They do not justify building a Facebook scraper. True
`/reel/` URLs may be evaluated in a later queue after this feasibility gate;
do not synthesize Reel URLs from video IDs.

## Evidence contract

Use only the `description` returned by the existing acquisition probe.
Preserve:

- original queued URL;
- resolved source URL when returned;
- creator/uploader;
- extractor/source name;
- exact description text;
- thumbnail URL when available;
- acquisition error when unavailable.

Do not combine search excerpts, comments, linked websites, audio transcripts,
or manually copied page text with the acquired description. A missing
description is an acquisition failure, not a parsing failure.

Create artifacts only when evidence exists:

```text
scratch/
  facebook_recipe_urls.txt
  facebook_recipe_acquisition_failures.json  # only after a failure
  facebook_recipe_cases/                     # only after a usable description
    001-short-name.json
  run_facebook_recipe_corpus.py               # only after the first case
```

Use the same direct JSON case shape as the archived Instagram corpus, changing
only `platform` to `facebook`. Set `source_text_kind` to `description`.

## Production-parser-first rule

For every usable description:

1. Freeze the exact source text.
2. Label `name`, `servings`, `raw_ingredients`, `steps`, and `tags` from the
   evidence before examining parser output.
3. Set `expected_complete` from the evidence, not from parser confidence.
4. Run `kitchensync.parsing.parse_recipe_text` unchanged.
5. Record the exact field differences and fallback status.

Do not create Facebook-specific parsing code merely because formatting differs
from Instagram. The production parser is intentionally platform-independent.

## When scratch code is justified

Do not write parser code for:

- login, redirect, or permission failures;
- a missing or truncated description;
- a source with no ingredients or no instructions;
- one ambiguous source;
- downstream ingredient normalization.

Scratch-only experimental code is justified only when at least two usable,
independently authored descriptions expose the same structural parser failure
and the expected result is unambiguous.

When that threshold is met:

1. Create the smallest helper or wrapper needed under `scratch/`.
2. Reuse the production parser rather than copying its implementation.
3. Keep the production result visible beside the experimental result.
4. Use structural evidence only: headings, adjacency, bullets, numbering,
   quantities, verbs, hashtags, and known boundary markers.
5. Never key a rule to a creator, page, URL, post ID, recipe title, or exact
   ingredient.
6. Discard the experiment if it fixes one case by regressing an accepted
   Facebook or Instagram case.

If a meaningful experiment would require copying a substantial production
module, stop and document the candidate production change for a later,
separately authorized pass.

## Sequential loop

For each queue entry:

1. Acquire evidence with:

   ```text
   uv run python scratch/social_import_probe.py --index N
   ```

2. On acquisition failure, append one compact record to
   `facebook_recipe_acquisition_failures.json` and continue.
3. Freeze a usable description and label its oracle with `accepted: false`.
4. Run the unchanged production parser and classify the result.
5. Mark a case accepted only after exact field and completeness agreement.
6. If a repeated structural failure meets the scratch-code threshold, make one
   small experiment and rerun the full Facebook corpus.
7. Run the archived Instagram corpus after every retained parsing experiment.
8. Run `uv run pytest` after every retained code change.
9. Continue through ordinary failures without replacing the source.

Keep acquisition, evidence labeling, parser behavior, and downstream
ingredient normalization as separate diagnoses.

## Metrics

Track:

- video-post acquisition: usable descriptions / 9;
- text-post acquisition controls: usable descriptions / 3;
- complete coverage: exact complete results / evidence-complete cases;
- complete precision: exact complete results / parser-complete results;
- fallback correctness: correct fallback results / evidence-incomplete cases;
- archived Instagram regressions.

The feasibility gate is successful when:

- all 12 URLs were attempted;
- at least six of the nine video posts produced usable descriptions;
- every production-complete result is materially correct;
- every evidence-incomplete case recommends fallback;
- complete coverage is at least 90% for usable evidence-complete cases;
- all 96 archived Instagram cases remain exact;
- `uv run pytest` passes;
- any retained experiment remains small and creator-independent.

The three text-post controls are reported separately and do not count against
the video acquisition threshold.

## Stop conditions

Stop and report rather than expanding scope when:

- Facebook broadly requires login/cookies and fewer than six video
  descriptions are usable;
- acquisition would require a new dependency or a Facebook scraper;
- a parser improvement would require production edits;
- a source creates an unresolved product-definition question;
- a simple general experiment cannot meet the precision boundary.

Do not begin a 40- or 100-source Facebook expansion in this pass. At the gate,
recommend expansion only if acquisition is reliable and the production parser
is already adequate or needs only a small, proven scratch experiment.

## Completion report

Report:

- all attempted URLs and acquisition outcomes;
- usable video and text-post counts;
- one-line result for every frozen case;
- coverage, precision, and fallback metrics;
- production-parser failures by structural class;
- scratch experiments retained or discarded;
- archived Instagram regression result;
- full test result;
- whether a larger Facebook queue is justified;
- any future production change, without implementing it.
