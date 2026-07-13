Project: [[../Kitchen Sync|Kitchen Sync]]

# Purpose
Portable source of truth for recipe files.

# Owns
- Human-readable recipe persistence
- Git-friendly diffs
- Recoverability without a database

# Does Not Own
- Fast search
- UI behavior
- Generated indexes

# Current Repo State
Markdown remains the planned durable source of truth, but recipe save layout and Markdown generation are not implemented yet.

Current next decision: define what happens when a parsed recipe is accepted and saved.

# Open Questions
- Exact recipe Markdown template
- Metadata/frontmatter conventions
- Image and attachment layout
