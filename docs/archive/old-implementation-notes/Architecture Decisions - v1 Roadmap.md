Project: [[Kitchen Sync]]

# Vision
Build a recipe application that is:
- Easy for my family to use every day.
- Stores recipes in a human-readable format.
- Uses Git for version control.
- Can eventually support desktop, web, and mobile.
- Can later support accounts, syncing, and collaboration.
- Allows recipes ranging from extremely simple to highly complex.
- Has a powerful import system for websites, PDFs, photos, and social media.

# Core Philosophy
Every layer has one responsibility.

| Component | Responsibility |
| --- | --- |
| Markdown | Source of truth / persistence |
| Git | Version history, branching, diffs |
| Database | Fast searching and indexing |
| Python Engine | Business logic, parsing, serialization |
| TypeScript App | User interface |

# Source of Truth
Recipes are stored as Markdown files.

Reasons:
- Human readable
- Easy to edit
- Portable
- Git-friendly
- Future-proof
- Easy backups

The application should never require a database to recover recipes.

# Internal Recipe Representation
The application never directly manipulates Markdown.

Instead:

```text
Markdown
      |
      v
Python Parser
      |
      v
Recipe Object (JSON / Python classes)
      |
      v
Application Logic
```

When saving:

```text
Recipe Object
      |
      v
Markdown Generator
      |
      v
Recipe.md
```

The Recipe Object is the in-memory representation. Markdown is persistence.

# Recipe Object Responsibilities
The Recipe Object should contain:
- Title
- Description
- Metadata
- Ingredients
- Ingredient references
- Steps
- Timing
- Dependencies
- Servings
- Notes
- Tags
- Source information
- Images
- Import metadata

The Recipe Object should be independent of the UI.

# Ingredient System
Ingredients are their own entities.

Example:

```text
Carrot
|-- Shredded Carrot
|-- Diced Carrot
|-- Julienned Carrot
`-- Roasted Carrot
```

Prepared ingredients are semantic variants, not Git branches.

Ingredient files can contain:
- Name
- Parent ingredient
- Tags
- Aliases
- Conversion rules
- Density
- Notes
- Preparation information

# Database
The database is not the source of truth. The database is an indexed cache.

Responsibilities:
- Recipe lookup
- Ingredient lookup
- Full-text search
- Tag search
- Fast filtering
- Relationship queries

If the database is deleted:

```text
Markdown
      |
      v
Rebuild Index
      |
      v
Database Restored
```

# Git
Git manages:
- History
- Branches
- Merges
- Rollbacks
- Diffs

Git should not know anything about recipe semantics. Recipe relationships belong in Markdown.

# Python Responsibilities
Python owns the engine.

Responsibilities:
- Markdown parsing
- Markdown generation
- Recipe validation
- Recipe object creation
- Ingredient handling
- Unit conversions
- Recipe scaling
- Import pipeline
- Website parsing
- PDF parsing
- OCR
- AI-assisted imports (future)
- Database indexing
- Search backend
- Business logic

Python exposes APIs that return JSON recipe objects.

# TypeScript Responsibilities
TypeScript owns the user experience.

Responsibilities:
- UI
- Recipe editor
- Ingredient editor
- Search interface
- Viewing recipes
- Calling Python APIs
- Managing application state
- Future mobile interface

TypeScript should contain as little business logic as possible.

# Communication Between UI and Engine
```text
TypeScript UI
        |
        | HTTP / JSON
        v
Python API
        |
        v
Recipe Object
```

The UI never manipulates Markdown directly.

# Import Pipeline
Future architecture:

```text
URL
Photo
PDF
Clipboard
Social Media
        |
        v
Importer
        |
        v
Python Parser
        |
        v
Recipe Object
        |
        v
Markdown
```

Importers may include:
- Website parser
- Schema.org parser
- OCR parser
- PDF parser
- AI cleanup parser
- Manual parser

AI should be the final fallback, not the first solution.

# Editing
Normal users:

```text
UI
 |
 v
Recipe Object
 |
 v
Markdown
```

Advanced users:

```text
Markdown
 |
 v
Parser
 |
 v
Recipe Object
```

Raw Markdown editing should be available but considered an advanced feature.

# Planned Timeline Features
Recipes may eventually support:
- Parallel cooking
- Timelines
- Dependencies
- Cooking graphs
- Prep stages
- Optional branches
- Reusable sub-recipes
- Scheduling

Example:

```text
Roast vegetables
        |
        |-- Start pasta
        |-- Make sauce
        `-- Plate together
```

# Expansion Plan: Cookbook
The Cookbook is the user's saved recipe library. It is distinct from the global recipe database.

Definitions:
- **Global recipe database:** All recipes known to the app, including imported recipes, indexed recipes, shared recipes, and recipes referenced by the system.
- **Cookbook:** Recipes intentionally saved by the user or family for regular use.

Cookbook responsibilities:
- Saved recipe collection
- Favorite recipes
- Search within saved recipes
- Filtering by tags, ingredients, meal type, cuisine, time, source, and difficulty
- Adding recipe ingredients to a shopping list
- Supporting recipe quantity multipliers before adding ingredients to the shopping list

The Cookbook should be backed by the same Recipe Object model.

The database can index Cookbook state for fast search and filtering, but saved recipe ownership should remain recoverable from Markdown metadata or a portable user-library file.

Example Cookbook metadata:
- Saved status
- Favorite status
- Family notes
- Last cooked date
- Cook count
- User tags
- Personal rating

# Shopping List
The shopping list is a dedicated tab in the app.

Shopping list responsibilities:
- Collect ingredients from one or more recipes
- Apply a multiplier before adding ingredients
- Scale quantities through the Python engine
- Group matching ingredients where possible
- Allow manual additions
- Allow checking off purchased items
- Preserve notes such as preparation, brand preference, or recipe source

Example flow:

```text
Recipe
      |
      v
Select servings or multiplier
      |
      v
Python scaling engine
      |
      v
Normalized ingredient list
      |
      v
Shopping List tab
```

The shopping list should reference Ingredient entities when possible, but also allow free-text items when normalization is uncertain.

# Expansion Plan: Pantry
The Pantry stores ingredients the user currently has. It is distinct from the global ingredient database.

Definitions:
- **Global ingredient database:** All ingredients ever referenced by recipes, imports, shopping lists, or pantry records.
- **Pantry:** The user's current available inventory.

Pantry responsibilities:
- Track ingredients currently on hand
- Store quantities and units
- Store optional location, expiration date, and notes
- Support "cook with what I have" search
- Support low-stock or missing-ingredient checks
- Support moving purchased shopping-list items into the pantry

The Pantry should reference global Ingredient entities instead of duplicating ingredient definitions.

Example Pantry item:
- Ingredient reference
- Quantity
- Unit
- Storage location
- Expiration date
- Notes
- Last updated date

Pantry architecture:

```text
Ingredient Entity
      |
      v
Pantry Item
      |
      v
User Inventory State
```

The global ingredient database answers "what is this ingredient?" The Pantry answers "do I currently have this ingredient?"

Future pantry features:
- Restock from receipt using OCR and photo import
- Barcode scanning
- Expiration reminders
- Substitution suggestions
- Automatic shopping-list gap detection
- Pantry-aware recipe recommendations

# Receipt Restock Pipeline
Future architecture:

```text
Photo of receipt
      |
      v
OCR parser
      |
      v
Receipt item extraction
      |
      v
Ingredient matching
      |
      v
User confirmation
      |
      v
Pantry update
```

AI may help clean receipt items and match ambiguous ingredients, but deterministic parsing and user confirmation should come first.

# Future Database Features
- Ingredient search
- Cook with what I have
- Recipe recommendations
- Ingredient aliases
- Shopping lists
- Pantry tracking
- Nutrition
- Similar recipe search

# Future Version Control Features
Git already provides:
- Commit history
- Branches
- Merging
- Rollback

Future application features:
- Recipe branching
- Compare recipe versions
- Visual diffs
- Merge assistance
- Shared repositories
- Collaborative editing

# Future Account System
Version 1:
- Shared Family Database

Version 2:
- Users
- Permissions
- Shared Libraries
- Cloud Sync
- Authentication

The core architecture should not depend on accounts.

# Possible Rust Integration
Rust is optional.

Potential responsibilities:
- High-performance parser
- Markdown serializer
- Conversion engine
- Recipe validation
- Dependency graph
- Timeline generation

Only migrate functionality to Rust if there is a clear benefit.

# Design Principles
- Markdown is always the source of truth.
- The database is disposable and rebuildable.
- Git manages history, not recipe semantics.
- Python owns the business logic.
- TypeScript owns the user interface.
- Keep clear boundaries between components.
- Make the Recipe Object the central abstraction.
- Prefer portability over lock-in.
- Build a small, usable MVP first.
- Optimize and expand only after the core workflow is solid.

# MVP
- Recipe object model
- Markdown parser and generator
- Ingredient model
- SQLite indexing
- Recipe search
- Recipe editor UI
- Import from common recipe websites
- Basic PDF/text import
- Git-compatible recipe storage
- Shared family recipe library

Everything else should build on this foundation.
