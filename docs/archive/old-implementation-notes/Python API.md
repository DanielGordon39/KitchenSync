Project: [[../Kitchen Sync|Kitchen Sync]]

# Purpose
Boundary between the UI and the recipe engine/search/state modules.

# Current Repo State
There is no external UI-facing API yet. Current Python entrypoints are package functions, especially `parse_recipe(...)` under `src/kitchensync/parsing`.

# Owns
- JSON request/response contracts
- API commands used by the UI
- Validation at the application boundary
- Coordination between engine, index, cookbook, pantry, and shopping list modules

# Does Not Own
- UI rendering
- Raw Markdown editing behavior
- Long-term source-of-truth storage decisions

# Open Questions
- HTTP API, local process RPC, or command runner?
- FastAPI or another Python API layer?
