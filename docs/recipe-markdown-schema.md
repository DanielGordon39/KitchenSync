# Recipe Markdown Schema v1

This document defines the first durable Markdown contract for saved KitchenSync recipes.

The exploratory shape in `scratch/recipe_input_probe.py` is the starting point: readable recipe Markdown, raw ingredient lines, and ordered steps. This schema keeps the durable recipe file human-readable and treats parsed ingredient fields as rebuildable parser/index output, not as saved Markdown content.

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

The `slug` is the filename stem and should be human-readable and stable enough for Git diffs. V1 does not require recipe identity to be stored in Markdown.

Attachments for a recipe should live under:

```text
recipes/{slug}/
```

## Identity Rules

- The database may generate a stable internal recipe ID when indexing the file.
- `slug` is derived from the canonical filename stem.
- `title` is the human-facing recipe name.
- `source.url` is import metadata, not identity.
- Renaming a recipe may change `title` and `slug`. Rename repair can be handled later if it becomes common.
- Re-importing the same URL should be treated as a duplicate-detection concern, not as the identity model.

## Required Structure

Every v1 recipe file must have:

1. A level-one heading containing the recipe title.
2. An optional description paragraph.
3. An optional fact bullet block.
4. An `## Ingredients` section.
5. A raw ingredient bullet list.
6. An `## Steps` section.
7. Ordered `### Step N` subsections.

## Fact Block

Recipe metadata may be represented as simple bullets after the description and before `## Ingredients`:

```markdown
- Servings: 2
- Source: HelloFresh
- Author: Michelle Doll Olson
- URL: https://www.hellofresh.com/recipes/blackened-chicken-penne-61b0d03ab3a03377ee6b1b04
- Imported from: recipe-scrapers
```

Fact block rules:

- Use `Label: value` bullets.
- The known v1 labels are `Servings`, `Source`, `Author`, `URL`, and `Imported from`.
- Unknown fact labels may be preserved by readers even if not indexed.
- Tags and images are deferred until the UI needs them.
- Large raw import artifacts, if retained later, should be sidecar files under `recipes/{slug}/`.

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
- Step metadata is optional. A step with only plain text bullets is valid v1 Markdown.

Advanced users may add an optional YAML metadata block immediately below a step heading:

````markdown
### Step 2

```yaml
type: cook
time_minutes: 8
ingredients:
  - chicken-breast
```

- Pat chicken dry.
- Season all over with blackening spice.
````

Step metadata rules:

- Metadata blocks are optional and should not be required by first-pass import or manual entry.
- `type`, when present, should match one of the recipe step types: `prep`, `cook`, `rest`, `assemble`, `plate`, `serve`, or `other`.
- `time_minutes`, when present, maps to a simple step-level time estimate.
- `ingredients`, when present, should contain canonical ingredient IDs or slugs.
- The step text remains the durable cooking instruction. Metadata enriches it but must not replace it.
- UI-created recipes may add metadata later; hand-authored recipes may omit it entirely.

Future TODO:

- Consider parser-assisted ingredient-to-step matching so KitchenSync can suggest `ingredients` metadata for each step.
- Consider richer cook-mode timing metadata only after the UI needs it.

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
# Blackened Chicken Penne

Creamy penne pasta with blackened chicken, scallions, and tomato.

- Servings: 2
- Source: HelloFresh
- Author: Michelle Doll Olson
- URL: https://www.hellofresh.com/recipes/blackened-chicken-penne-61b0d03ab3a03377ee6b1b04
- Imported from: recipe-scrapers

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

- `recipes.recipe_id` from an internal database-generated ID.
- `recipes.slug` from the filename stem.
- `recipes.markdown_path` from the file path.
- `recipes.title` from the level-one heading.
- `recipes.servings`, `recipes.source_*`, `recipes.author`, and `recipes.imported_from` from the fact block.
- `recipes.time_estimate_minutes` from recipe time metadata when available from parser or UI input.
- `recipe_tags` from recipe tags when available from parser or UI input.
- `recipe_ingredients.raw_text` from the raw ingredient bullet list.
- `recipe_ingredients.*` parsed fields by re-running the ingredient parser over each ingredient bullet.
- `recipe_ingredients.ingredient_id` by matching parser output and raw text against the canonical ingredient database, auto-creating minimal canonical ingredient records in v1 when no match exists.
- V2 ingredient candidates from unmatched or low-confidence ingredient observations that need review.
- `recipe_steps.*` from `### Step N` sections.
- Search text from title, slug, source fields, author, imported-from marker, ingredient bullets, parser-derived ingredient names, and tags. Step text and description remain Markdown content, not v1 search-index inputs.

The database may store a full parsed JSON snapshot for speed, but that snapshot is rebuildable cache data.

Ingredient candidate review state is durable app state, not recipe Markdown content. V1 normal recipe imports do not create ingredient candidates, but v2 candidate approval should update canonical ingredient data or aliases rather than rewriting the recipe solely to store parser-derived fields.

## Validation Rules

A v1 parser should reject or flag files when:

- The level-one heading is missing.
- Step numbers are missing, duplicated, skipped, or out of order.

Warnings are acceptable for:

- Missing servings.
- Missing source metadata.
- Empty tags.
- Ingredient lines the parser cannot structure cleanly.

## Probe Alignment

`scratch/recipe_input_probe.py` demonstrates the v1 body shape:

- `# {recipe.name}`
- Optional description
- `## Ingredients`
- Raw ingredient bullets
- `## Steps`
- `### Step N`

The production Markdown writer should keep that durable shape. Parsed ingredient fields should remain parser/index output, not part of saved recipe files.
