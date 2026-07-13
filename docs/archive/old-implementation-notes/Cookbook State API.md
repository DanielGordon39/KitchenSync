Project: [[../Kitchen Sync|Kitchen Sync]]

# Status
This note has been split conceptually into two layers:
- [[Global Recipe Database]] - v1 recipe database available through the Cookbook tab.
- [[Personal Cookbook State API]] - v2 account-backed saved/favorite/share layer.

# Decision
The Cookbook tab is the user-facing recipe database UI. It replaces a generic Recipes tab.

For v1, the Cookbook tab can operate directly over the Global Recipe Database.

For v2, Personal Cookbook state can add account-backed saved recipes, favorites, notes, ratings, and sharing with other accounts.
