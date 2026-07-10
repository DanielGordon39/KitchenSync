# Design Drift Policy

## Purpose

Keep the repository implementation, repository docs, and Obsidian planning notes aligned enough that future work remains coherent.

## When To Flag Drift

Flag likely design drift when:

- Code adds a new module, model, service, API, storage layer, or architectural boundary not reflected in Obsidian or repo docs.
- Code changes contradict current Obsidian boundary diagrams.
- A feature becomes stable enough that planning notes should be reviewed or promoted into repo docs.
- Repo docs and Obsidian notes describe different ownership boundaries.
- Implementation starts depending on behavior that the design notes still describe as future or undecided.

## What To Do

When drift is detected:

1. State the specific mismatch.
2. Identify the likely affected note or repo doc.
3. Ask whether the user wants docs/notes reviewed or updated.

Do not silently rewrite Obsidian notes unless the user asks.

## Source Priority

- Implementation truth: repo code, tests, and configuration.
- Planning context: Obsidian notes and diagrams.
- Durable public project guidance: repo docs.

If sources conflict, do not pick a winner without user confirmation.
