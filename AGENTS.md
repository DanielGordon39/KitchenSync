# KitchenSync Agent Instructions

These instructions apply to the entire repository.

## Required Context

Before modifying this repository, read:

- `.agents/design-sources.md`
- `.agents/ai-work-policy.md`
- `.agents/design-drift-policy.md`
- `.agents/commit-policy.md`

Use the Obsidian notes listed in `.agents/design-sources.md` as design and planning context. Treat repository code and tests as implementation truth.

## Work Boundaries

- Default to collaboration: explain, research, compare options, inspect documentation, and provide examples before attempting implementation.
- Treat phrases like "I want to implement", "let's make", "should we", or design discussion as requests for assistance and planning, not automatic permission to edit code.
- Treat explicit requests like "code this", "make the code change", "implement this in code", or "update the files" as entering the code-change confirmation path.
- Documentation and harmless boilerplate may be created or updated directly.
- Non-trivial code, business logic, model changes, migrations, dependency changes, and behavior-changing configuration require explicit secondary user confirmation before editing.
- Writing non-trivial code is a last resort after clarifying design, checking existing docs, and considering whether an existing library/package fits the problem.
- Do not silently rewrite Obsidian notes. If design drift is detected, ask whether the user wants the notes reviewed or updated.
- Do not run `git commit`, create branches, push, or rewrite git history unless explicitly asked.

## Commit Suggestions

After a meaningful feature or structural change, suggest a git commit with one Conventional Commit message. Prefer:

- `feat: ...`
- `fix: ...`
- `docs: ...`
- `test: ...`
- `refactor: ...`
- `chore: ...`

Do not stage or commit changes unless the user explicitly requests it.
