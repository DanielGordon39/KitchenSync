Project: [[../Kitchen Sync|Kitchen Sync]]

# Purpose
Future v2 account-backed layer for personal or shared saved recipe state.

# Owns
- Saved recipes
- Favorites
- Personal or family notes
- Ratings
- Last cooked date
- Cook count
- Sharing with other accounts

# Distinction
This is not required for v1. V1 can use the Global Recipe Database directly through the Cookbook tab.

# Public API Questions
- Did this user save this recipe?
- Did this user favorite this recipe?
- What notes or ratings are attached to this recipe for this account or family?
- Which other accounts can access this personal cookbook?

# Open Questions
- Should personal cookbook state live in a local file, cloud database, or both?
- How should shared family state merge with personal state?
