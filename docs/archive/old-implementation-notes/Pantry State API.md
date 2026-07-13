Project: [[../Kitchen Sync|Kitchen Sync]]

# Purpose
Tracks what the user currently has.

# Owns
- Current inventory
- Quantities and units
- Storage location
- Expiration date
- Low-stock state
- Move purchased shopping-list items into pantry

# Distinction
The Pantry references the Global Ingredient Database but does not define ingredients globally.

# Public API Questions
- Do I have this ingredient?
- How much do I have?
- Is it expired or low?
- What recipes can I cook with current inventory?

# Open Questions
- How precise should quantity tracking be in v1?
- Should pantry state be file-backed, database-backed, or both?
