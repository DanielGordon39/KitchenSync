Project: [[../Kitchen Sync|Kitchen Sync]]

# Purpose
Owns the user experience: screens, tabs, editing workflows, and visual state.

# Likely Technologies
- TypeScript
- Desktop/web UI framework: undecided
- Calls [[Python API]] over JSON

# Public API Usage
- Should call API endpoints or commands.
- Should not parse Markdown directly.
- Should not perform recipe scaling or ingredient normalization directly.

# Open Questions
- Desktop-first framework: Tauri, Electron, web-first, or other?
- Should mobile be planned now or deferred?
