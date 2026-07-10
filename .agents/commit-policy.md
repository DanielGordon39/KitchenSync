# Commit Policy

## When To Suggest A Commit

After a meaningful change, suggest that the user commit the work and provide one proposed commit message.

Meaningful changes include:

- New feature or model
- New documentation structure
- New agent or automation guidance
- Project configuration change
- Test addition
- Refactor that changes structure

Do not suggest a commit after trivial discussion-only turns or read-only inspection.

## Commit Message Format

Use Conventional Commit format:

```text
type: concise imperative message
```

Allowed initial types:

- `feat`
- `fix`
- `docs`
- `test`
- `refactor`
- `chore`

Examples:

```text
docs: add agent guidance and design source references
feat: add initial recipe domain models
chore: update project scaffolding
```

## Git Operations

- Do not stage files unless explicitly asked.
- Do not commit unless explicitly asked.
- Do not push unless explicitly asked.
- If asked for a commit message, inspect the current worktree state first.
