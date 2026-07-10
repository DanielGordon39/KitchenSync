# Recipe Markdown Schema v1

This document defines the first durable Markdown contract for saved KitchenSync recipes.

The exploratory shape in `scratch/recipe_parse_probe.py` is the starting point: readable recipe Markdown, raw ingredient lines, and ordered steps. This schema keeps the durable recipe file human-readable and treats parsed ingredient fields as rebuildable parser/index output, not as saved Markdown content.

## Purpose

Recipe Markdown files are the source of truth for saved recipes. The database may index these files, cache parsed fields, and support search, but recipe content must remain recoverable from Markdown.

## Scope

Schema v1 covers the recipe fields needed by the current parsing scaffold:

- Recipe identity
- Recipe title and optional description
- Servings
- Tags
- Source/import metadata
- Raw ingredient lines
- Ordered recipe steps
- Recipe notes
- Recipe-level images

Schema v1 does not yet cover durable parsed ingredient overrides, pantry state, shopping-list state, personal cookbook state, advanced cook-mode timelines, dependency graphs, or global ingredient definition files.

## File Location

Saved recipes should live at:

```text
recipes/{slug}.md
```

The `slug` should be human-readable and stable enough for Git diffs. The stable recipe identity is still `recipe_id`, not the filename.

Attachments for a recipe should live under:

```text
recipes/{slug}/
```

## Identity Rules

- `recipe_id` is the stable application identity.
- `slug` is the canonical filename stem.
- `title` is the human-facing recipe name.
- `source.url` is import metadata, not identity.
- Renaming a recipe may change `title` and possibly `slug`, but must not change `recipe_id`.
- Re-importing the same URL should be treated as a duplicate-detection concern, not as the identity model.

## Required Structure

Every v1 recipe file must have:

1. YAML frontmatter.
2. A level-one heading matching the recipe title.
3. An optional description paragraph.
4. An `## Ingredients` section.
5. A raw ingredient bullet list.
6. An `## Steps` section.
7. Ordered `### Step N` subsections.

## Frontmatter

Required fields:

```yaml
---
schema_version: 1
recipe_id: recipe_blackened_chicken_penne_61b0d03a
slug: blackened-chicken-penne
title: Blackened Chicken Penne
---
```

Optional fields:

```yaml
servings: 2
tags:
  - weeknight
  - pasta
source:
  name: HelloFresh
  url: https://www.hellofresh.com/recipes/blackened-chicken-penne-61b0d03ab3a03377ee6b1b04
  author:
import:
  source_type: url
  imported_from: recipe-scrapers
  raw_fields:
    yields: 2 servings
images:
  - uri: blackened-chicken-penne/hero.jpg
    alt_text: Finished blackened chicken penne
    caption:
```

Field rules:

- `schema_version` must be `1`.
- `recipe_id` must be unique across saved recipes.
- `slug` should match the filename stem.
- `title` must match the level-one heading text.
- `tags` are lowercase slugs.
- Empty optional scalar values may be omitted or left blank.
- `images.uri` may be relative to the recipe file.
- `import.raw_fields` is for compact parser/debug values, not full raw HTML or OCR dumps.

Large raw import artifacts, if retained, should be sidecar files referenced from frontmatter:

```yaml
import:
  raw_artifacts:
    html: blackened-chicken-penne/import.html
    scraper_json: blackened-chicken-penne/recipe-scrapers.json
```

## Body

The level-one heading is required:

```markdown
# Blackened Chicken Penne
```

An optional description may appear immediately after the heading:

```markdown
Creamy penne pasta with blackened chicken, scallions, and tomato.
```

The description ends at the next heading.

## Ingredients Section

The ingredient list is durable data. These lines preserve the accepted parser or user-entered ingredient text.

```markdown
## Ingredients

- 10 ounce Chicken Breast Strips
- 6 ounce Penne Pasta
- 2 scallions
```

Ingredient rules:

- Use one bullet per ingredient line.
- Preserve ingredient wording users expect to see while cooking.
- Parser output should be generated from these lines during indexing.
- If parser output is wrong in v1, correct the ingredient bullet text before saving.
- Durable structured ingredient overrides are deferred until there is a clear product need.
- Ingredient-specific notes may be written in the line itself.

If parsing fails, preserve or edit the ingredient line as normal recipe text:

```markdown
- a splash of vinegar, to taste
```

## Steps Section

Steps use ordered headings:

```markdown
## Steps

### Step 1

- Bring a large pot of salted water to a boil.

### Step 2

- Pat chicken dry.
- Season all over with blackening spice.
```

Step rules:

- Step headings must use `### Step N`.
- Step numbers must start at `1` and increase by `1`.
- Bullets under a step are part of that step's text.
- Multiple bullets under one step preserve order.
- Empty steps are invalid.

## Notes Section

Recipe-level notes are optional:

```markdown
## Notes

- Reduce blackening spice if cooking for kids.
- Add pasta water gradually; sauce thickens quickly.
```

These map to recipe-level notes, not ingredient notes or cook-history notes.

## Complete Example

```markdown
---
schema_version: 1
recipe_id: recipe_blackened_chicken_penne_61b0d03a
slug: blackened-chicken-penne
title: Blackened Chicken Penne
servings: 2
tags:
  - pasta
  - weeknight
source:
  name: HelloFresh
  url: https://www.hellofresh.com/recipes/blackened-chicken-penne-61b0d03ab3a03377ee6b1b04
  author:
import:
  source_type: url
  imported_from: recipe-scrapers
  raw_fields:
    yields: 2 servings
images: []
---

# Blackened Chicken Penne

Creamy penne pasta with blackened chicken, scallions, and tomato.

## Ingredients

- 10 ounce Chicken Breast Strips
- 6 ounce Penne Pasta
- 2 scallions

## Steps

### Step 1

- Bring a large pot of salted water to a boil.

### Step 2

- Pat chicken dry.
- Season all over with blackening spice.

## Notes

- Keep raw ingredient text for parser review.
```

## Database Rebuild Mapping

An index rebuild should derive database rows from Markdown as follows:

- `recipes.recipe_id` from frontmatter `recipe_id`.
- `recipes.slug` from frontmatter `slug`.
- `recipes.markdown_path` from the file path.
- `recipes.title` from frontmatter `title` and the level-one heading.
- `recipes.servings`, `recipes.source_*`, `recipes.imported_from`, and `recipes.tags` from frontmatter.
- `recipe_ingredients.raw_text` from the raw ingredient bullet list.
- `recipe_ingredients.*` parsed fields by re-running the ingredient parser over each ingredient bullet.
- `recipe_ingredients.ingredient_id` by matching parser output and raw text against the canonical ingredient database when confidence is high enough.
- `ingredient_candidates` from unmatched or low-confidence ingredient observations that need review.
- `recipe_steps.*` from `### Step N` sections.
- Full-text search text from title, description, ingredient bullets, parser-derived ingredient names, steps, tags, and notes.

The database may store a full parsed JSON snapshot for speed, but that snapshot is rebuildable cache data.

Ingredient candidate review state is durable app state, not recipe Markdown content. Approving a candidate should update canonical ingredient data or aliases rather than rewriting the recipe solely to store parser-derived fields.

## Validation Rules

A v1 parser should reject or flag files when:

- Frontmatter is missing.
- `schema_version` is not `1`.
- `recipe_id`, `slug`, or `title` is missing.
- The level-one heading does not match `title`.
- Step numbers are missing, duplicated, skipped, or out of order.

Warnings are acceptable for:

- Missing servings.
- Missing source metadata.
- Empty tags.
- Ingredient lines the parser cannot structure cleanly.

## Probe Alignment

`scratch/recipe_parse_probe.py` already demonstrates the v1 body shape:

- `# {recipe.name}`
- Optional description
- `## Ingredients`
- Raw ingredient bullets
- `## Steps`
- `### Step N`

The production Markdown writer should keep that durable shape and add v1 frontmatter. Parsed ingredient fields should remain parser/index output, not part of saved recipe files.
