# Ingredient Markdown Schema v1

This document defines the durable Markdown contract for canonical KitchenSync ingredients.

Ingredient files are human-editable source files. The database indexes these files for fast lookup, matching, packaging lookup, pantry support, and shopping-list logic.

## Purpose

Ingredient Markdown answers: what is this ingredient?

It stores canonical app knowledge such as:

- Stable ingredient identity
- Parent ingredient relationship
- Matching aliases
- Grocery category and storage metadata
- Common packaging/store units
- Unit conversions
- Human notes and matching guidance

Recipe Markdown still answers: what does this recipe use?

## File Location

Canonical ingredients should live at:

```text
ingredients/{slug}.md
```

Examples:

```text
ingredients/chicken.md
ingredients/chicken-breast.md
ingredients/penne-pasta.md
ingredients/blackening-spice.md
```

Candidate ingredient files, if made file-backed later, should live separately:

```text
ingredients/_candidates/{candidate_slug}.md
```

## Format Strategy

Use Markdown files with three levels of structure:

1. YAML frontmatter for identity and small stable fields.
2. YAML fenced sections for large structured lists.
3. Markdown prose sections for notes and matching guidance.

This avoids oversized frontmatter while keeping ingredient data portable and Obsidian-friendly.

## Identity Rules

- `ingredient_id` is the stable application identity.
- `slug` is the canonical filename stem.
- `name` is the human-facing canonical name.
- `parent_id` references another canonical ingredient when this ingredient is a narrower child.
- Renaming `name` or `slug` must not change `ingredient_id`.
- Aliases are matching hints, not identity.

Parent examples:

```text
chicken
└── chicken_breast

tomato
└── roma_tomato

pasta
└── penne_pasta
```

## Required Structure

Every v1 ingredient file must have:

1. YAML frontmatter.
2. A level-one heading matching the ingredient name.

Standard optional sections:

1. `## Aliases`
2. `## Packaging`
3. `## Conversions`
4. `## Matching Guidance`
5. `## Notes`

## Frontmatter

Required fields:

```yaml
---
schema_version: 1
ingredient_id: chicken_breast
slug: chicken-breast
name: Chicken Breast
---
```

Optional fields:

```yaml
parent_id: chicken
category: meat
storage_area: refrigerated
default_unit: ounce
tags:
  - protein
  - poultry
```

Field rules:

- `schema_version` must be `1`.
- `ingredient_id` must be unique across canonical ingredients.
- `slug` should match the filename stem.
- `name` must match the level-one heading text.
- `parent_id`, when present, must reference an existing canonical ingredient.
- `category`, `storage_area`, `default_unit`, and `tags` are normalized slugs.

## Aliases Section

Aliases are stored as a YAML list:

````markdown
## Aliases

```yaml
- chicken breast
- boneless chicken breast
- boneless skinless chicken breast
- chicken breast strips
```
````

Alias rules:

- Aliases are used for ingredient matching.
- Aliases should be lowercase unless casing is semantically meaningful.
- Aliases should not duplicate another canonical ingredient's primary name unless the matching workflow explicitly resolves the ambiguity.
- New aliases may come from approved ingredient candidates.

## Packaging Section

Packaging records common purchase forms:

````markdown
## Packaging

```yaml
- package_id: chicken_breast_tray_20_oz
  name: tray
  quantity: 20
  unit: ounce
  store_unit: package
  notes: Common grocery package
- package_id: chicken_breast_value_pack_40_oz
  name: value pack
  quantity: 40
  unit: ounce
  store_unit: package
```
````

Packaging rules:

- `package_id` is stable within the ingredient file.
- `name` is the human-facing package name.
- `quantity` and `unit` describe how much ingredient the package contains.
- `store_unit` describes what the shopping list buys, usually `package`, `bag`, `box`, `can`, `jar`, `bottle`, or `unit`.
- Packaging enriches shopping-list decisions; it does not change recipe quantities.

## Conversions Section

Conversions define known equivalences:

````markdown
## Conversions

```yaml
- conversion_id: pound_to_ounce
  from_quantity: 1
  from_unit: pound
  to_quantity: 16
  to_unit: ounce
- conversion_id: cup_diced_to_ounce
  from_quantity: 1
  from_unit: cup
  to_quantity: 4.5
  to_unit: ounce
  preparation: diced
  confidence: estimated
```
````

Conversion rules:

- `conversion_id` is stable within the ingredient file.
- Conversions may be exact or estimated.
- `preparation` is optional and should be used when the conversion only applies to a specific prepared form.
- `confidence` should be `exact`, `estimated`, or `unknown` when provided.

## Matching Guidance Section

Matching guidance is Markdown prose for human and future parser behavior:

```markdown
## Matching Guidance

Match "chicken breast strips" to this ingredient unless the source clearly refers to a packaged prepared meal product.
```

This section is not required to be machine-parsed in v1.

## Notes Section

Notes are human-facing:

```markdown
## Notes

Use for boneless chicken breast recipe ingredients. Keep whole chicken, thighs, wings, and ground chicken as separate ingredients.
```

## Complete Example

````markdown
---
schema_version: 1
ingredient_id: chicken_breast
slug: chicken-breast
name: Chicken Breast
parent_id: chicken
category: meat
storage_area: refrigerated
default_unit: ounce
tags:
  - protein
  - poultry
---

# Chicken Breast

## Aliases

```yaml
- chicken breast
- boneless chicken breast
- boneless skinless chicken breast
- chicken breast strips
```

## Packaging

```yaml
- package_id: chicken_breast_tray_20_oz
  name: tray
  quantity: 20
  unit: ounce
  store_unit: package
  notes: Common grocery package
- package_id: chicken_breast_value_pack_40_oz
  name: value pack
  quantity: 40
  unit: ounce
  store_unit: package
```

## Conversions

```yaml
- conversion_id: pound_to_ounce
  from_quantity: 1
  from_unit: pound
  to_quantity: 16
  to_unit: ounce
  confidence: exact
```

## Matching Guidance

Match "chicken breast strips" to this ingredient unless the source clearly refers to a packaged prepared meal product.

## Notes

Use for boneless chicken breast recipe ingredients. Keep whole chicken, thighs, wings, and ground chicken as separate ingredients.
````

## Database Rebuild Mapping

An ingredient index rebuild should derive database rows from Markdown as follows:

- `ingredients.ingredient_id` from frontmatter `ingredient_id`.
- `ingredients.slug` from frontmatter `slug`.
- `ingredients.name` from frontmatter `name` and the level-one heading.
- `ingredients.parent_ingredient_id` from frontmatter `parent_id`.
- `ingredients.category`, `storage_area`, `default_unit`, and tags from frontmatter.
- `ingredient_aliases` from the `## Aliases` YAML block.
- `ingredient_packaging` from the `## Packaging` YAML block.
- `ingredient_conversions` from the `## Conversions` YAML block.
- Full-text search text from name, aliases, matching guidance, notes, category, storage area, and tags.

The database may store parsed snapshots for speed, but canonical ingredient definitions are recoverable from Markdown.

## Candidate Interaction

Ingredient candidates are review workflow state. They may start in the database and later become file-backed if portability is needed.

Approving a candidate may:

- Create a new ingredient Markdown file.
- Add an alias to an existing ingredient file.
- Add packaging or conversion details to an existing ingredient file.
- Reject or ignore the candidate without changing canonical ingredient files.

## Validation Rules

A v1 parser should reject or flag files when:

- Frontmatter is missing.
- `schema_version` is not `1`.
- `ingredient_id`, `slug`, or `name` is missing.
- The level-one heading does not match `name`.
- `parent_id` references a missing ingredient.
- YAML fenced sections are malformed.
- Alias, packaging, or conversion IDs collide in a way that makes indexing ambiguous.

Warnings are acceptable for:

- Missing aliases.
- Missing packaging.
- Missing conversions.
- Missing category or storage metadata.
- Parentless top-level ingredients.

