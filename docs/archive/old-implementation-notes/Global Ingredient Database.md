Project: [[../Kitchen Sync|Kitchen Sync]]

# Purpose
Canonical ingredient knowledge known to the app.

This answers what an ingredient is, not whether the user currently has it.

# Persistence Decision
Canonical ingredients are Markdown-backed.

The durable source of truth is ingredient Markdown files such as:

```text
ingredients/{slug}.md
```

The ingredient database is a rebuildable index/cache derived from those files.

Repo schema reference:

```text
C:\Coding\Personal\KitchenSync\docs\ingredient-markdown-schema.md
```

# Owns
- Ingredient identities
- Parent/variant relationships
- Aliases
- Packaging and store units
- Grocery category and storage metadata
- Conversion metadata
- Density and preparation metadata when known
- Matching guidance and human notes

# Does Not Own
- Recipe ingredient text; recipe Markdown owns what each recipe uses.
- Pantry inventory; [[Pantry State API]] owns what is currently on hand.
- Shopping-list checked state; [[Shopping List API]] owns planned purchases.
- Unreviewed parser output; candidate review state owns pending decisions.

# Candidate Review Boundary
New or uncertain ingredient observations from recipe imports, recipe Markdown indexing, manual entry, or receipt parsing should enter an ingredient candidate queue instead of automatically becoming canonical ingredient records.

Approving a candidate may:
- Create a new ingredient Markdown file.
- Add an alias to an existing ingredient Markdown file.
- Add packaging or conversion details to an existing ingredient Markdown file.
- Reject or ignore the candidate without changing canonical ingredient files.

# Database Rebuild
An ingredient index rebuild should read ingredient Markdown and populate:
- Canonical ingredient rows
- Alias lookup rows
- Packaging rows
- Conversion rows
- Category and storage indexes
- Matching/search indexes

If the ingredient index is deleted, it should be recoverable from ingredient Markdown files.

# Open Questions
- How much ingredient metadata is needed for v1?
- Should ingredient candidates start database-only or become file-backed under `ingredients/_candidates/`?
