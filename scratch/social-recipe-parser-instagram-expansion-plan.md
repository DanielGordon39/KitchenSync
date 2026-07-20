# Instagram Creator Expansion Loop Plan

## Purpose

Expand the accepted Phase 1 corpus from 12 to as many as 100 unique Instagram
recipes. Start with the creators the user supplied, then discover additional
creators through popular high-protein recipe posts. Keep the proven
freeze-label-run-improve-regress loop unchanged. Do not add another platform
during this pass.

This is still scratch research. It does not authorize production promotion,
recipe saving, dependency changes, or edits outside `scratch/`.

## Start gate

Before discovery begins:

- Read `AGENTS.md`, the required `.agents/` context, the completed Phase 1 plan,
  and this plan completely.
- Confirm the Phase 1 corpus runner reports 12 accepted cases with 100%
  complete coverage, complete precision, and fallback correctness.
- Confirm `uv run pytest` passes; the Phase 1 completion baseline is 35 tests.
- Capture `git status --short` and verify the user has committed the intended
  Phase 1 baseline.
- The user must explicitly start this expansion pass. Codex must not stage or
  create the baseline commit.

## Creator discovery order

Start with the creators represented by the supplied Phase 1 URLs:

1. Joe Chu
2. Jalal
3. Tom Walsh
4. Calvin Kang / cooklikeimbook
5. Kyle Smith
6. Ben Chelin
7. Jess & Dan / Tofu Club
8. Bella / Cooking Made Easy

Resolve each actual profile from its supplied reel page. Do not guess a handle
from a display name when the reel can confirm the profile.

After those creators have been inspected, use Instagram's public search,
Explore, hashtag, and recommended-post surfaces to find other popular
high-protein recipe posts. Treat the post's confirmed author as the next
creator, inspect that creator's public page for up to three eligible recipes,
then move on to another creator.

"Popular" means Instagram surfaced the post as top, popular, or recommended,
or the page shows clear engagement relative to nearby results. Do not require a
fixed like or view threshold, because those counts may be hidden or
incomparable. Popularity is only a discovery route; it is not a parser field or
an acceptance criterion.

## Read-only Instagram discovery

Public creator-page navigation is authorized for source discovery. It must stay
read-only:

- Do not like, comment, follow, save, share, message, or change account state.
- Do not open or use ephemeral Stories or Live content.
- A signed-in browser session may be used when Instagram requires it, but only
  to view public profiles, search results, and posts.
- Do not download media or add scraping or browser-automation dependencies.

Select candidates before running the parser against any newly selected source.
This prevents the current parser from influencing which captions enter the
corpus.

## Candidate selection

Target up to 88 new unique Instagram post or reel URLs. Together with the 12
accepted Phase 1 sources, that yields up to 100 unique corpus cases.

Use this creator-by-creator loop:

1. Visit each supplied creator in the listed order.
2. Within that profile, inspect public posts newest to oldest and select up to
   two new posts that present a specific recipe or preparation.
3. Move to the next supplied creator even when fewer than two are eligible.
4. After the supplied list, find one new creator through a popular
   high-protein recipe post.
5. Confirm the creator from the post, inspect that creator's page, and select up
   to three eligible recipes.
6. Move to another discovered creator and repeat until 88 new URLs are selected
   or eligible public discovery is exhausted.

Never select more than two new sources from a Phase 1 creator or three from a
newly discovered creator during this pass. Do not repeatedly mine one large
account to fill the corpus.

Eligibility is based on the post, not on whether its caption appears easy for
the parser. A selected recipe remains eligible when its caption is incomplete;
that becomes a fallback case after acquisition. Skip only:

- Any of the 12 Phase 1 source shortcodes.
- A shortcode already selected during this discovery pass.
- Non-recipe announcements, general lifestyle posts, and unrelated promotions.
- Posts discovered outside the supplied set that do not present a high-protein
  recipe or preparation.
- Ephemeral, private, deleted, or otherwise inaccessible content.

Preserve each selected URL exactly as discovered, including its query string.
Use the Instagram media shortcode only for duplicate detection.

After all candidates are selected, append one `# Instagram creator expansion`
section to `scratch/social_recipe_urls.txt` and add the selected URLs in final
creator-discovery order. Do not edit the existing queue entries or uncomment the
cross-platform examples. Once acquisition starts, freeze the appended queue;
record failures instead of replacing URLs mid-loop.

If discovery produces fewer than 88 eligible URLs, proceed with the smaller
frozen queue and report why. Do not exceed 100 total unique corpus sources and
do not begin another platform to fill a shortfall.

## Acquisition and corpus contract

Keep the Phase 1 contract:

- Use only the Instagram `description` returned by the existing `yt-dlp` path.
- Do not download media, require ffmpeg, transcribe audio, or combine caption
  text with another evidence source.
- Preserve the discovered URL as `source_url` and record the confirmed creator.
- Record acquisition failures in one
  `scratch/social_recipe_acquisition_failures.json` file, creating it only if
  failures occur.
- Freeze agent-labeled expectations before viewing the parser result.
- Score exactly `name`, `servings`, `raw_ingredients`, `steps`, and `tags`.
- Set `expected_complete` from caption evidence: a supported name, at least one
  ingredient, and at least one instruction.
- Keep tags as literal lowercase hashtags in source order.

Continue global case identities from Phase 1. With a full 88-source expansion,
the new queue and case indices are 014 through 101. The final active queue has
101 entries but represents 100 unique sources because Phase 1 entries 1 and 2
are duplicates. Do not create case 002.

Store new cases beside the accepted Phase 1 cases in
`scratch/social_recipe_cases/` so the existing corpus runner remains the one
regression boundary.

## Sequential loop

For each appended queue entry:

1. Acquire the description or record the failure and continue.
2. Freeze the source and agent-labeled expected fields with `accepted: false`.
3. Run the unchanged parser and record the baseline difference.
4. Make only the smallest creator-independent structural rule change needed.
5. Run the complete aggregate corpus, including all 12 Phase 1 cases.
6. Run `uv run pytest` after each retained parser change.
7. Keep a rule only when it improves the new case without regressing an
   accepted case.
8. Mark the case accepted only after exact field and completeness agreement.
9. Continue through isolated acquisition and parser failures.

The Phase 1 rule discipline and stop conditions still apply. Creator names,
handles, titles, post IDs, URLs, and exact ingredient phrases are never valid
parser-rule inputs.

## Completion gate

Stop after every selected URL has been attempted; do not stop early because a
metric is already met.

Report new-pass and aggregate metrics separately:

- Selected and attempted URLs, unique usable captions, acquisition failures,
  creator distribution, supplied-versus-discovered creator counts, and the
  final total corpus size.
- Exact complete coverage.
- Exact complete precision.
- Fallback correctness.
- One-line results for every new case.
- Any retained rules and discarded attempts.
- Whether all 12 accepted Phase 1 cases remain exact.
- Final `uv run pytest` result and changed-file scope.

The technical target remains at least 90% complete coverage, 100% complete
precision, 100% fallback correctness, no accepted regressions, and no changes
outside `scratch/`. Prefer the best simple result over brittle exceptions.

The new expectations remain provisional until the user audits them. Only after
this Instagram pass reaches its stopping point and is audited should a separate
plan choose and introduce one new platform.

## New-session prompt

Start the next task with:

```text
Read AGENTS.md, scratch/social-recipe-parser-scratch-loop-plan.md, and
scratch/social-recipe-parser-instagram-expansion-plan.md completely.

I authorize the Instagram creator expansion described in the expansion plan,
including read-only navigation of supplied creator pages and public Instagram
search, Explore, hashtag, recommended-post, creator-profile, and post surfaces.
I authorize code/data edits under scratch/ only. Treat the rest of the
repository as read-only.

First select and freeze a queue of up to 88 new recipe posts. Start with the
eight supplied creators and select at most two new recipes from each. Then
repeatedly find a creator through popular high-protein recipe posts, inspect
that creator's page, select at most three eligible new recipes, and continue to
another creator. Process every selected URL sequentially using the existing
description-only acquisition, frozen-oracle, corpus-regression, and pytest
loop. Do not add another platform. Stop at 100 total unique corpus cases,
exhausted eligible discovery, the expansion completion gate, or an explicit
blocker.
```
