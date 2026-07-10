# Design Sources

Use these sources to understand KitchenSync's intended structure and design boundaries.

## Obsidian Planning Context

Treat these notes as design and planning context, not executable source of truth:

- `C:\Obsidian\Nexus\Efforts\KitchenSync\KitchenSync.md`
- `C:\Obsidian\Nexus\Efforts\KitchenSync\Architecture Decisions - v1 Roadmap.md`
- `C:\Obsidian\Nexus\Efforts\KitchenSync\Diagrams\Diagram Index.md`
- `C:\Obsidian\Nexus\Efforts\KitchenSync\Implementation\`

## Repository Truth

Treat repository code, tests, and project configuration as implementation truth.

When code and notes differ, do not assume either side should be changed automatically. Flag the mismatch and ask whether the user wants the docs, notes, or implementation reviewed.

## Current Boundary Expectations

- Recipe models describe recipe content.
- Cookbook models describe collections and user/cookbook-specific relationship state.
- Pantry models describe current inventory, not global ingredient definitions.
- Shopping list models describe planned purchases.
- Markdown remains the long-term portable recipe source of truth.
- Database/index layers are rebuildable caches unless explicitly designed otherwise.
