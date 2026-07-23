# TikTok Recipe Parsing Loop Plan

Status: preparation only; source discovery, live acquisition, and parsing have
not started.

## Goal

Determine how public TikTok recipe videos differ from Instagram and Facebook
at the acquisition and parser-input boundaries. Use the existing production
social-text parser first, keep experiments under `scratch/tiktok/`, and make no
production edits during this pass.

The loop is:

```text
public TikTok recipe URL
  -> acquire description, source metadata, and caption availability
  -> freeze the exact description and minimal evidence
  -> label expected recipe fields before viewing parser output
  -> run kitchensync.parsing.parse_recipe_text unchanged
  -> distinguish acquisition, missing-evidence, and parsing failures
  -> add the smallest TikTok scratch experiment only when justified
  -> rerun TikTok plus archived Instagram regressions
```

The output is evidence for
`scratch/facebook-tiktok-comparison-plan.md`, not a production implementation.

## Current implementation facts

At plan creation:

- `scratch/social_import_probe.py` already labels canonical, mobile, and
  `vm.tiktok.com` URLs as TikTok and uses the installed `yt-dlp` acquisition
  path.
- The installed `yt-dlp` version is `2026.07.04`.
- Its TikTok extractors support canonical
  `www.tiktok.com/@creator/video/<numeric-id>` URLs and `vm.tiktok.com`,
  `vt.tiktok.com`, and `www.tiktok.com/t/` short redirects.
- Extracted evidence can include description, uploader, resolved URL,
  thumbnails, and subtitles.
- The extractor explicitly handles challenge cookies and may report that
  login or fresh cookies are required.
- `scratch/social_import_probe.py::identify_platform(...)` does not currently
  label `vt.tiktok.com` or `www.tiktok.com/t/` as TikTok. If selected discovery
  URLs use those shapes, correct only this scratch classifier before the live
  loop; do not change production URL handling.
- `kitchensync.parsing.parse_recipe_text(...)` is platform-independent and must
  receive the first parsing attempt for every usable description.

Recheck these facts at the start of execution because extractor behavior can
change independently of KitchenSync.

## Authority and boundaries

Allowed:

- Read production models, parser APIs, tests, and documentation.
- Discover and inspect public TikTok recipe videos without changing account
  state.
- Use `scratch/social_import_probe.py` with the TikTok queue.
- Create and edit TikTok queues, cases, reports, acquisition diagnostics, and
  minimal experiments under `scratch/tiktok/`.
- Make the tiny scratch-only URL-classification correction described above if
  an observed queue URL requires it.
- Run frozen corpora, focused checks, and `uv run pytest`.

Not allowed:

- Do not edit `src/`, `ui/`, production configuration, dependencies, or
  production behavior.
- Do not save imported recipes.
- Do not add an LLM, transcription service, scraper, browser-automation
  framework, or media-processing dependency.
- Do not like, comment, follow, save, share, message, or otherwise change
  TikTok account state.
- Do not silently replace acquisition failures.
- Do not combine description and subtitle text before their separate evidence
  value has been measured.

## Start gate

Before discovery:

1. Read `AGENTS.md`, its required policy/design sources, this plan,
   `scratch/facebook-recipe-parser-loop-plan.md`, and the archived Instagram
   expansion results.
2. Confirm the active Facebook worktree changes are understood and preserved.
3. Run the archived Instagram corpus with the production parser:

   ```text
   uv run python scratch/archive/instagram/run_social_recipe_corpus.py
   ```

4. Run `uv run pytest`.
5. Confirm the installed TikTok extractor list and version.
6. Confirm the execution environment can access public TikTok pages. A
   platform challenge is an acquisition result, not permission to add
   credentials or a new scraper.

## Read-only source discovery

Select 12 public recipe-video URLs before parsing any selected description.
Discovery may use public search, creator pages, hashtags, recommendations, and
search-engine results, but it must remain read-only.

The frozen queue should contain:

- at least eight canonical
  `https://www.tiktok.com/@creator/video/<numeric-id>` URLs;
- at least two short redirect URLs using `vm.tiktok.com` or `vt.tiktok.com`;
- at least four independent creators;
- a natural mix of detailed and sparse descriptions.

Choose sources because the post presents a specific recipe or preparation, not
because its text appears easy for the parser. Do not inspect parser results
during selection.

Append selected URLs to `scratch/tiktok/tiktok_recipe_urls.txt` in discovery
order. Preserve each URL exactly, including query strings. Once acquisition
begins, freeze the queue and record failures without replacement.

Use the numeric video ID only for duplicate detection. Attempt duplicate queue
entries but freeze and score the first usable occurrence once.

## Acquisition evidence contract

Use `yt-dlp` through the existing probe as the first acquisition path:

```text
uv run python scratch/social_import_probe.py \
  scratch/tiktok/tiktok_recipe_urls.txt --index N
```

For every URL record:

- exact queued URL;
- resolved source URL when returned;
- extractor/source name;
- uploader;
- description availability and exact description text;
- subtitle/caption availability without merging its text;
- thumbnail availability;
- acquisition outcome or exact failure class.

The primary parser input for this pass is the acquired `description`. Preserve
subtitles only as separate acquisition evidence.

Classify outcomes explicitly:

- `description-usable`;
- `description-sparse`;
- `description-missing-subtitles-present`;
- `description-and-subtitles-missing`;
- `login-or-challenge`;
- `redirect-failure`;
- `unavailable-or-unsupported`;
- another precise observed acquisition failure.

Do not use search snippets, comments, linked recipe sites, manually copied page
text, on-screen text, or transcript text as a substitute for the acquired
description.

## Minimal artifacts

Create only what the observed loop needs:

```text
scratch/tiktok/
  tiktok_recipe_urls.txt
  tiktok-recipe-parser-loop-plan.md
  tiktok_recipe_acquisition_failures.json  # only after a failure
  tiktok_recipe_cases/                     # only after usable text exists
    001-short-name.json
  run_tiktok_recipe_corpus.py              # only after the first case
  tiktok-recipe-parser-results.md           # at the completion gate
```

Use the archived Instagram case shape with:

- `platform: "tiktok"`;
- `source_text_kind: "description"`;
- exact source text;
- expected `name`, `servings`, `raw_ingredients`, `steps`, and `tags`;
- `expected_complete`, `accepted`, and review notes.

Do not copy the production parser or introduce a platform framework.

## Production-parser-first rule

For each nonblank acquired description:

1. Freeze the source text before parser changes.
2. Label expected fields from the evidence with `accepted: false`.
3. Set `expected_complete` from the source evidence: supported name, at least
   one ingredient, and at least one instruction.
4. Run `kitchensync.parsing.parse_recipe_text(...)` unchanged.
5. Record exact field and fallback differences.
6. Mark the case accepted only after exact field and completeness agreement.

A sparse description that omits recipe content should produce a correct
fallback. Do not force completeness based on information visible only in the
video.

## Separate acquisition and parser experiments

Do not write parsing code for login, challenge, redirect, empty-description, or
subtitle-only outcomes.

If the generic probe cannot preserve an already returned TikTok metadata field
needed by the comparison, a small `scratch/tiktok/tiktok_acquisition_probe.py`
wrapper may be created. It must call the installed extractor, preserve raw
evidence, and avoid media download or browser automation.

Parser experiments are justified only when at least two usable descriptions
from independent creators expose the same unambiguous structural parsing
failure.

When justified:

1. Create the smallest helper or wrapper under `scratch/tiktok/`.
2. Reuse the production parser rather than copying it.
3. Keep production and experimental results visible side by side.
4. Use structural evidence only: headings, adjacency, bullets, numbering,
   quantities, verbs, hashtags, and boundary markers.
5. Never key logic to a creator, handle, video ID, URL, title, or exact
   ingredient.
6. Keep an experiment only when it improves the repeated failure without
   regressing accepted TikTok or Instagram cases.

If meaningful evaluation requires substantial copied production code, stop and
record the candidate change for the later promotion plan.

## Sequential loop

For every frozen queue entry:

1. Acquire evidence or record the failure and continue.
2. Freeze usable descriptions and label expectations before parsing.
3. Run the production parser unchanged.
4. Classify the result as complete-correct, fallback-correct,
   complete-incorrect, fallback-incorrect, or acquisition failure.
5. Retain only justified, minimal scratch experiments.
6. Run every accepted TikTok case after each retained experiment.
7. Run the archived Instagram corpus after each retained parsing experiment.
8. Run `uv run pytest` after each retained code change.
9. Continue through ordinary failures without replacing sources.

Do not begin subtitle/transcript parsing during this loop. The completion report
may recommend a separate subtitle evidence experiment if enough cases are
`description-missing-subtitles-present`.

## Metrics and feasibility gate

Track:

- metadata acquisition success / 12;
- nonblank description availability / 12;
- subtitle availability / 12;
- canonical versus short-link acquisition;
- login/challenge and redirect failures;
- complete coverage;
- complete precision;
- fallback correctness;
- archived Instagram regressions.

The feasibility gate is successful when:

- all 12 URLs were attempted;
- source metadata was acquired for at least eight;
- at least six produced nonblank descriptions;
- at least four independent creators are represented among usable evidence;
- every production-complete result is materially correct;
- every evidence-incomplete case recommends fallback;
- complete coverage is at least 90% for evidence-complete descriptions;
- all 96 archived Instagram cases remain exact;
- `uv run pytest` passes;
- retained scratch code is small and evidence-driven.

Subtitle availability is reported separately and does not make an otherwise
incomplete description complete.

## Stop conditions

Stop and report when:

- fewer than eight sources yield metadata because TikTok broadly requires
  login, challenge resolution, or fresh cookies;
- fewer than six usable descriptions remain after all 12 attempts;
- acquisition requires a new dependency or scraper;
- evaluation requires media download, OCR, or transcription;
- a parser improvement requires production edits;
- a simple experiment cannot preserve complete precision.

Do not expand to a larger TikTok corpus in this pass.

## Completion report

Write `scratch/tiktok/tiktok-recipe-parser-results.md` containing:

- discovery and creator distribution;
- all attempted URLs and acquisition outcomes;
- canonical versus short-link results;
- description and subtitle availability;
- one-line parser result for every frozen case;
- complete coverage, precision, and fallback correctness;
- acquisition and parser failure classes;
- scratch experiments retained or discarded;
- archived Instagram regression result;
- full test result;
- evidence-backed TikTok-versus-Instagram observations;
- whether larger TikTok research is justified;
- candidate future production work without implementing it.

This report becomes an input to
`scratch/facebook-tiktok-comparison-plan.md`.

## Goal Mode handoff prompt

Start a new chat from the KitchenSync repository with:

```text
/goal Execute the TikTok recipe parsing feasibility pass through its documented
completion gate. Do not begin a larger TikTok expansion.

Before acting, read AGENTS.md and all required policy/design sources,
scratch/tiktok/tiktok-recipe-parser-loop-plan.md,
scratch/facebook-recipe-parser-loop-plan.md, and
scratch/archive/instagram/social-recipe-parser-instagram-expansion-results.md
completely.

Discover and freeze the 12-source queue specified by the TikTok plan before
evaluating parser output. Preserve URLs exactly and keep failures in place.
Use scratch/social_import_probe.py for the first acquisition attempt and the
production parse_recipe_text implementation for the first parse of every
usable description.

Treat everything outside scratch/ as read-only. Do not edit production code,
dependencies, configuration, tests, UI behavior, or save imported recipes.
Keep acquisition failures separate from parsing failures. Preserve subtitle
availability as evidence but do not merge subtitle or transcript text into the
description during this goal.

Write scratch-only code only at the thresholds and boundaries defined in the
plan. Continue through ordinary failures. Run the TikTok corpus, archived
Instagram corpus, and uv run pytest at the documented checkpoints.

Finish by writing
scratch/tiktok/tiktok-recipe-parser-results.md and mark the goal complete only
after the full feasibility report is finished.
```
