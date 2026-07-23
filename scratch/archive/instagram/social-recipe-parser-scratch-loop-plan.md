# Social Recipe Parser Scratch Loop Plan

> Status: Phase 1 completed its technical gate with 13 queue attempts, 12
> unique usable Instagram cases, 100% complete coverage, 100% complete
> precision, and 100% fallback correctness. The follow-on pass is defined in
> `scratch/social-recipe-parser-instagram-expansion-plan.md`.

## Purpose

Develop and evaluate a deterministic social-media recipe text parser entirely inside `scratch/` before any code is considered for promotion into `src/kitchensync/`.

The working loop is:

```text
social URL
  -> acquire Instagram description/caption evidence
  -> freeze the evidence as a local corpus case
  -> run the deterministic parser
  -> identify the smallest general failure
  -> make one small rule change
  -> rerun every frozen case and the repository test suite
  -> repeat until all 13 active queue entries have been attempted
```

This phase produces experimental code and evidence. It must not change production behavior or save imported recipes into the KitchenSync library.

## Preparation gate

Phase 1 starts only after the user reviews and commits the complete scratch
baseline and this plan. Codex must not stage or create that commit.

Before the commit:
- Confirm `.agents/design-sources.md` lists both machine-specific KitchenSync note roots and instructs agents to use whichever exists.
- Capture `git status --short` and the scratch diff so all existing modifications are recognized as baseline work.
- Leave `scratch/social_recipe_urls.txt` unchanged.
- Confirm `uv run pytest` passes. The preparation baseline was 35 passing tests.

After the commit, the user must explicitly start Phase 1 before URL acquisition or parser changes begin.

## Authority and boundaries

Before doing anything, read the repository `AGENTS.md` and its required context files.

Allowed:
- Read any repository code, models, tests, and documentation needed to understand the existing contracts.
- Import and reuse existing KitchenSync models and parsing helpers from `src/kitchensync/`.
- Create and edit files under `scratch/`.
- Run scratch scripts, focused checks, and `uv run pytest`.
- Use the supplied public social-media URLs to acquire source evidence.

Not allowed in this phase:
- Do not edit `src/`, `tests/`, `docs/`, `ui/`, `pyproject.toml`, `uv.lock`, or other non-scratch project files.
- Do not stage, commit, push, reset, or discard pre-existing user changes.
- Do not add dependencies. Stop and explain if an additional dependency appears necessary.
- Do not call an LLM or other AI service from the parser or corpus runner.
- Do not save a parsed candidate through the canonical KitchenSync save boundary.
- Do not automate likes, comments, follows, messages, or creator-profile actions.

Production code and tests are read-only references. Scratch code may depend on their public models and helpers, but it must not alter them.

## Existing scratch starting point

Build on the current files instead of creating a second implementation:
- `scratch/social_recipe_urls.txt` owns the input URL queue.
- `scratch/social_import_probe.py` owns live evidence acquisition and readable diagnostics.
- `scratch/recipe_text_parser.py` owns deterministic, platform-independent text parsing.
- `scratch/README.md` documents the scratch responsibility boundary.

Preserve the existing raw, readable recipe evidence while also showing structured results. Do not replace source-facing text with normalized-only output.

## Minimal new artifacts

Create only what the loop actually needs:

```text
scratch/
  social_recipe_urls.txt
  social_import_probe.py
  recipe_text_parser.py
  run_social_recipe_corpus.py
  social_recipe_acquisition_failures.json  # only when failures occur
  social_recipe_cases/
    001-short-name.json
    002-short-name.json
    ...
```

When acquisition failures occur, store them as one JSON array:

```json
[
  {
    "queue_index": 4,
    "source_url": "https://www.instagram.com/...",
    "reason": "No description text was available."
  }
]
```

Do not introduce a framework, registry, plugin system, configuration layer, database, or class hierarchy for this experiment.

`run_social_recipe_corpus.py` should be one small executable regression runner. It should load every JSON case, call the current deterministic parser, compare the result with the expected fields, and print a compact scoreboard. It exits nonzero for malformed case data, parser execution errors, or a regression in an accepted case; known unaccepted failures remain visible without failing the run.

## First corpus

The starting queue is already present in `scratch/social_recipe_urls.txt`:
- Process all 13 uncommented entries returned by `read_urls(...)`, in file order.
- Leave the URL file unchanged; the `# For the loop` marker is only a visual divider.
- The queue contains 12 unique Instagram URLs because one URL appears twice.
- Attempt both occurrences of the repeated URL. Freeze and score its first usable occurrence once; report the second occurrence as a duplicate of that case.
- Determine creator names during acquisition. The supplied selection is accepted even if the final creator mix differs from the preferred 3–5 creators.
- Variation among headings, bullets, numbered steps, narrative captions, hashtags, nutrition blocks, calls to action, and incomplete recipes should be recorded rather than assumed.
- A URL that cannot be acquired does not count as a usable parsed recipe. Record the acquisition failure and continue through the remaining supplied URLs.

Phase 1 should produce at least 10 usable unique frozen cases from the 12 unique URLs. The duplicate cannot satisfy this minimum. If fewer than 10 unique cases are usable after all 13 entries have been attempted, stop and report which sources need replacement instead of performing unrelated discovery.

Use only the `description` returned by the existing `yt-dlp` acquisition path;
for Instagram this is the post caption. Preserve creator and source URL metadata,
but do not download media, require ffmpeg, add speech-to-text machinery, or
combine the caption with transcript text. A missing description is an
acquisition failure, not a reason to expand dependencies.

Do not perform broad recipe discovery during Phase 1. The supplied Instagram collection is the corpus source. Do not navigate connected creators or search for popular recipes unless the user later authorizes the expansion.

## Frozen case format

Use one JSON file per recipe and only standard-library JSON handling. Keep the format direct and human-reviewable. A case should contain enough information to reproduce parsing without network access:

```json
{
  "id": "001-short-name",
  "queue_index": 1,
  "platform": "instagram",
  "creator": null,
  "source_url": "https://www.instagram.com/...",
  "source_text_kind": "description",
  "source_text": "Frozen caption text...",
  "expected": {
    "name": "Recipe name or null",
    "servings": null,
    "raw_ingredients": ["1 cup example"],
    "steps": ["Do the first thing."],
    "tags": ["dinner"]
  },
  "expected_complete": true,
  "accepted": false,
  "notes": []
}
```

Store only evidence needed by the parser and reviewer. Do not preserve the full `yt-dlp` result unless a specific field proves necessary.

Keep the first queue index as the case identity. `expected_complete` describes
the evidence rather than the current parser: it is true only when the caption
supports a recipe name, at least one ingredient, and at least one instruction.
Set `accepted` to true only after the five expected fields match exactly and
the parser's fallback status agrees with `expected_complete`.

Phase 1 scores only `name`, `servings`, `raw_ingredients`, `steps`, and `tags`.
Description, notes, ingredient normalization, and Recipe-model conversion are
diagnostics. Tags are literal source hashtags, lowercased in source order; this
does not approve them as production KitchenSync tags.

Before changing parser code for a new recipe:
1. Inspect the frozen source evidence.
2. Write the expected recipe fields based on that evidence.
3. Run the current parser and record the baseline difference.

This ordering prevents the parser's current output from silently becoming its own expected answer.

## Meaning of a correct result

A complete parse is correct only when:
- The recipe name is supported by the source.
- All source ingredient lines are included, in order, without instructions, nutrition, hashtags, or promotional text leaking into the ingredient list.
- All available instruction steps are included, in order, without ingredient or promotional text leaking into them.
- Servings are populated only when the source states them reliably.
- Tags come from genuine tag evidence.
- A partial or ambiguous source is flagged as incomplete instead of confidently presented as complete.

Judge raw ingredient extraction before judging downstream ingredient normalization. Existing KitchenSync ingredient models and helpers may be used to preview normalization, but a normalization issue must not be misdiagnosed as a social-text boundary issue.

Track these rates over unique frozen cases:
- **Complete coverage:** exact correct-complete results divided by cases where `expected_complete` is true.
- **Complete precision:** exact correct-complete results divided by every result the parser reports complete.
- **Fallback correctness:** every case where `expected_complete` is false recommends fallback.

False completeness is worse than an explicit fallback. The target is 100% complete precision, 100% fallback correctness, and at least 90% complete coverage across cases whose source evidence is complete. Do not penalize a correct fallback merely because an acquired caption omits part of the recipe.

## Sequential improvement loop

Process URLs one at a time in file order. Do not edit the parser for several unseen failures at once.

For each URL:
1. Acquire its Instagram description and minimal creator/source metadata.
2. If acquisition fails, record the failure separately and continue. Do not change parsing rules to compensate for missing evidence.
3. If the URL already has a frozen case, acquire and evaluate it again, report the duplicate, and do not create or score a second case.
4. Freeze first-seen usable source text using its original queue index.
5. Define the expected fields from the frozen evidence with `accepted` set to false.
6. Run the current parser against that case before editing code.
7. Classify the smallest root failure, such as heading recognition, section boundaries, bullet interpretation, numbered steps, nutrition exclusion, promotional-text exclusion, or incomplete-source detection.
8. Make the smallest structural rule change that addresses the failure.
9. Run the complete unique-source corpus.
10. Run `uv run pytest` after each retained parser change. Reuse the last passing result when acquisition or case labeling caused no parser change.
11. Review the scratch diff for accidental complexity or unrelated edits.
12. Set `accepted` to true only after exact field and completeness agreement. Otherwise keep the case as a visible known failure.
13. Keep a parser change only if it improves the result without breaking accepted cases. If it does not, manually undo only the lines changed by the current attempt.
14. Continue to the next queue entry without waiting for routine user confirmation.

## Rule discipline

Prefer structural evidence over special cases:
- Headings, adjacency, blank-line boundaries, bullets, numbering, quantities, verbs, hashtags, and known nutrition markers are valid rule inputs.
- A creator name, post ID, URL, exact recipe title, or exact ingredient phrase is not a valid rule input.
- Do not add an exception merely to make one ambiguous case green. Mark that case incomplete when no simple general rule exists.
- Prefer changing one shared decision point over patching several downstream symptoms.
- Reuse the standard library and already-installed dependencies.
- Add a helper only when it makes repeated logic clearer.
- Delete or simplify a failed experiment rather than preserving it behind configuration.

The parser should remain easy to read from top to bottom. Accuracy gained through a growing pile of unexplained thresholds or overlapping regexes is not a successful result.

## Progress reporting

After each case, print a compact line containing:

```text
[3/13 entries; 2/12 unique] creator / short-name: complete-correct | usable corpus 2/2 | pytest pass
```

Keep working through ordinary parser failures. Pause only when:
- Authentication or a permission boundary blocks the remaining corpus rather than one isolated URL.
- A new dependency appears necessary.
- A product decision would materially change what KitchenSync considers a recipe.
- Continuing would require editing outside `scratch/`.

Do not pause for one unavailable source. Record it, continue through the queue,
and request replacements only at the completion gate if fewer than 10 unique
usable cases were acquired.

## Phase 1 completion gate

Stop and return a report after all 13 active entries have been attempted and every usable unique source has been frozen and evaluated. Do not stop early at 10.

Phase 1 is successful when:
- The report shows 13 attempted entries and 12 unique source URLs, including the duplicate mapping.
- Every usable unique case runs offline through the corpus runner.
- At least 10 unique usable cases were acquired. If not, return an acquisition report and request replacement URLs.
- At least 90% of cases with complete source evidence produce exact correct complete candidates.
- Every candidate reported as complete is materially correct.
- Every case with incomplete source evidence returns an explicit fallback result.
- Previously accepted cases do not regress.
- `uv run pytest` passes without changes outside `scratch/`.
- The scratch implementation remains small and readable.

If the 90% coverage target cannot be reached without brittle special cases or substantial new machinery, stop at the best simple result. Explain the unresolved failure classes and why further rules would be poor tradeoffs. Do not build a larger architecture just to satisfy the number.

The final report must include:
- Queue entries attempted, unique URLs, usable unique cases, the duplicate mapping, and acquisition failures.
- Complete coverage and complete precision.
- Fallback correctness.
- A one-line result for each corpus case.
- The small general rules added or changed.
- Any rule attempts discarded because they caused regressions or complexity.
- The full test-suite result.
- Files changed under `scratch/`.
- Whether the parser appears ready for a separate promotion plan.
- A recommendation for the next 40 recipes, but no Phase 2 implementation.

All expected fields are agent-labeled during the loop, so these metrics remain
provisional until the user audits the frozen corpus once at this gate. If that
audit changes an expectation, rerun the unchanged parser before considering a
new rule.

## Later phases

Do not begin these phases during the first session.

The next pass starts only after the user reviews the Phase 1 report and uses
`scratch/social-recipe-parser-instagram-expansion-plan.md`:
- Expand from 12 to as many as 100 unique Instagram cases: first inspect the
  Phase 1 creators, then find additional creators through popular high-protein
  recipe posts. Select no more than two new recipes from each Phase 1 creator
  or three from each newly discovered creator.
- Require every accepted Phase 1 case to remain passing.
- Do not add a new platform until that Instagram expansion is complete and
  audited.

Further corpus-size and unseen-validation targets should be planned after the
first new-platform pass rather than assumed here.

Promotion into `src/kitchensync/` is a separate, explicitly approved task. Scratch success does not authorize production edits.

## Implementation-session prompt

After the user has reviewed and committed the preparation baseline, start a normal implementation session with:

```text
Read AGENTS.md and scratch/social-recipe-parser-scratch-loop-plan.md completely.

I approve Phase 1 and explicitly authorize code and data edits under scratch/
only. Treat the rest of the KitchenSync repository as read-only, although you
may import and run its existing models, helpers, and tests.

Follow the plan sequentially through all 13 active URL entries returned by
read_urls(...). Attempt the repeated URL twice but freeze and score it once.
Freeze and evaluate every usable unique case, with at least 10 unique usable
cases required for Phase 1. Preserve all pre-existing changes. Do not stop for
an ordinary failed recipe: diagnose it, make the smallest general improvement,
rerun the entire corpus and uv run pytest after retained parser changes, then
continue. Stop at the Phase 1 completion gate or at an explicit blocker.
```
