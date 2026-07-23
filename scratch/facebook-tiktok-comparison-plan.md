# Facebook–TikTok Scratch Comparison and Promotion Plan

Status: waiting for both platform feasibility passes.

## Goal

Compare observed Facebook and TikTok acquisition and parser behavior, resolve
their differences in scratch, and produce one narrow production-promotion
proposal. Do not edit production code during this comparison.

This is the bridge between platform research and a later explicitly authorized
implementation task.

## Start gate

Do not start until these durable reports exist:

- `scratch/facebook-recipe-parser-results.md`;
- `scratch/tiktok/tiktok-recipe-parser-results.md`.

Also read:

- both platform loop plans and frozen queues;
- both platform case directories and acquisition failure records;
- `scratch/archive/instagram/social-recipe-parser-instagram-expansion-results.md`;
- `docs/next-plans.md`;
- the current production social parser and Instagram acquisition boundary.

Run both platform corpus runners, the archived Instagram corpus, and
`uv run pytest` before drawing conclusions.

If either feasibility pass stopped at its acquisition floor, compare the
observed limitation but do not design a production adapter around missing
evidence.

## Comparison principle

Compare evidence, not platform reputation or ideal APIs.

Keep four questions separate:

1. Can KitchenSync recognize and validate the URL?
2. Can the installed acquisition path obtain stable public evidence?
3. What text evidence is actually available?
4. Can the shared production parser interpret that text correctly?

An acquisition difference is not a parser difference. A source that omits the
recipe is not a failed parse. A browser/search excerpt is not a substitute for
acquired evidence.

## Capability matrix

Create a table with one Facebook and one TikTok column covering:

| Area | Required observation |
| --- | --- |
| URL shapes | Accepted canonical, redirect, post, video, and short-link forms |
| Redirect behavior | Whether queued and resolved URLs remain traceable |
| Anonymous access | Successes, login requirements, cookies, and challenges |
| Metadata | Source name, author/uploader, resolved URL, thumbnail |
| Primary text | Description availability, length, and recipe completeness |
| Secondary text | Captions/subtitles availability without automatic merging |
| Failure behavior | Stable unsupported versus transient acquisition errors |
| Parser results | Coverage, precision, fallback correctness, failure classes |
| Review evidence | What the user must see before accepting an import |
| Image evidence | Thumbnail availability only; no media/frame work in this pass |

Include counts and representative frozen case IDs for every conclusion.

## Difference classification

Classify each observed difference into exactly one boundary:

- **Shared parser behavior:** platform-independent text structure handled by
  `kitchensync.parsing.social`.
- **Platform acquisition:** URL validation, redirects, authentication,
  metadata mapping, and description/subtitle retrieval.
- **Import orchestration:** choosing a platform adapter, preserving raw
  evidence, and returning a reviewable failure.
- **Review UI evidence:** source attribution, warnings, fallback status, and
  optional secondary-text availability.
- **Deferred media research:** transcription, OCR, downloaded media, and frame
  selection.

Do not solve a platform acquisition issue with parser rules or a missing-source
issue with guessed recipe content.

## Scratch reconciliation loop

Use the existing frozen cases and reports first. Add code only when a concrete
comparison cannot be answered from them.

For each difference:

1. Identify representative Facebook, TikTok, and Instagram cases.
2. State the current production behavior.
3. State the desired shared behavior without naming a new abstraction.
4. Test whether the existing production parser already satisfies it.
5. If not, prototype the smallest structural experiment under `scratch/`.
6. Run every Facebook, TikTok, and archived Instagram case.
7. Keep the experiment only when it improves the shared contract without
   platform, creator, URL, title, or ingredient special cases.
8. Record acquisition-specific behavior separately.

Do not create a platform registry, plugin system, base adapter class, or copied
parser in scratch. A direct function per observed platform is enough if code is
needed at all.

## Normalized evidence decision

Determine whether both platforms can feed the existing parser with one plain
description string or whether import orchestration needs a small source
evidence record.

If a record is justified, define only observed fields:

- queued source URL;
- resolved source URL;
- platform/source name;
- author/uploader;
- exact primary description;
- thumbnail candidate;
- secondary-text availability;
- acquisition warnings.

Do not add transcript content, engagement metrics, media downloads, platform
API objects, or speculative fields.

Prototype the shape in scratch data or a minimal scratch type before proposing
production ownership. The production proposal must preserve the current
Instagram API until an explicitly authorized implementation says otherwise.

## Production-promotion gate

Recommend production implementation only when:

- both feasibility passes reached their documented acquisition floors;
- supported and unsupported URL shapes are explicit;
- queued and resolved URL behavior is understood;
- metadata mappings are backed by frozen examples;
- missing descriptions and secondary-text-only cases have clear fallback
  behavior;
- shared parser experiments pass all Facebook, TikTok, and Instagram cases;
- platform-specific work is confined to acquisition/validation;
- the review-first, no-save-before-acceptance contract remains unchanged;
- no new runtime dependency is required, or the need is separately justified;
- the full repository test suite passes.

The comparison may recommend promoting one platform before the other. Do not
force a combined production change merely because both were researched
together.

## Required production proposal

Write a file-by-file proposal, not production code. For each proposed change
include:

- responsibility and public API;
- why existing code cannot cover it;
- Facebook, TikTok, or shared ownership;
- compatibility effect on Instagram;
- focused unit and frozen-evidence tests;
- explicit non-goals;
- rollback or unsupported behavior.

Prefer:

- separate small acquisition/validation functions per supported platform;
- the existing shared `parse_recipe_text(...)` entrypoint;
- one orchestration decision point;
- the existing review-before-save boundary.

Defer:

- transcript/OCR/media pipelines;
- background import jobs;
- platform plugin frameworks;
- broad UI redesign;
- automatic saving;
- large-corpus expansion unless feasibility evidence calls for it.

## Completion deliverable

Write `scratch/facebook-tiktok-comparison-results.md` containing:

- completed capability matrix;
- evidence-backed similarities and differences;
- shared parser regression results;
- scratch experiments retained or discarded;
- normalized evidence decision;
- platform support recommendation;
- exact production file/API/test proposal;
- risks and explicitly deferred work;
- recommended order for later production implementation.

Do not edit production files during this goal.

## Goal Mode handoff prompt

Use only after both platform result documents exist:

```text
/goal Compare the completed Facebook and TikTok recipe-import feasibility
results, reconcile proven differences in scratch, and produce the documented
production-promotion proposal. Do not edit production code.

Before acting, read AGENTS.md and all required policy/design sources,
scratch/facebook-tiktok-comparison-plan.md, both platform loop plans and result
documents, the frozen Facebook and TikTok evidence, the archived Instagram
results, docs/next-plans.md, and the current production social parser and
Instagram acquisition boundary.

Run all available Facebook, TikTok, and archived Instagram corpus checks plus
uv run pytest. Build the evidence-backed capability matrix. Keep acquisition,
parser, orchestration, and review-UI differences separate.

Make only minimal experiments under scratch/ when frozen evidence cannot answer
a comparison. Do not add dependencies, save recipes, edit src/, ui/, tests, or
production configuration, and do not build a platform framework.

Finish by writing scratch/facebook-tiktok-comparison-results.md with the
normalized evidence decision and an exact file/API/test proposal for a later
explicitly authorized production task. Mark the goal complete only after that
document and all required validation results are finished.
```
