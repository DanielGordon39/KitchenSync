Project: [[../Kitchen Sync|Kitchen Sync]]

# Purpose
Represents all recipes available to the app in v1.

# Owns
- The app-wide recipe collection
- Recipe lookup by ID or slug
- Relationship to Markdown recipe files
- The conceptual database that the Cookbook tab browses

# Distinction
This is not the Personal Cookbook. It answers what recipes exist in the app, not which recipes a specific user saved, favorited, rated, or shared.

# Public API Questions
- What recipes exist?
- What recipe should this ID open?
- What recipes are available to search and filter?
- Which Markdown file backs this recipe?

# Open Questions
- Is the global recipe database just Markdown plus index, or does it need explicit metadata?
- How should imported-but-unreviewed recipes appear?
