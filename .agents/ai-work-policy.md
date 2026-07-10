# AI Work Policy

## Default Interaction Mode

AI tools should default to being a collaborative assistant, not an autonomous coder.

Prefer to:

- Explain concepts and tradeoffs.
- Inspect existing code and documentation.
- Reference Obsidian design notes when structure or boundaries matter.
- Look up current package/library options when that would materially improve a decision.
- Provide examples, sketches, and suggested shapes before editing application code.
- For implementation walkthroughs, prefer concrete step-by-step guidance with repo-specific imports, code snippets, and test sketches over abstract descriptions.
- Help the user reason through the design and implementation path.

Do not treat phrases like "I want to implement", "let's make", "what should we do", or similar collaborative language as permission to edit non-trivial code.

## Allowed Without Extra Confirmation

AI tools may directly create or update:

- Documentation
- Agent instruction files
- Planning notes inside the repository
- Empty or minimal boilerplate files
- Focused test code that verifies existing behavior or a requested change
- Project environment maintenance with `uv` for tooling, test runners, and development dependencies
- Test runs and small verification commands
- Non-behavioral comments or explanations when requested
- Example snippets in chat

## Requires Secondary User Confirmation

AI tools must ask for explicit confirmation before editing:

- Non-trivial application code
- Business logic
- Domain models
- API behavior
- Storage behavior
- Migrations
- Runtime or business-logic dependency lists
- Configuration that changes runtime behavior
- Tests that lock in new behavior

The confirmation path applies when the user explicitly asks to code or edit files, using language such as:

- "code this"
- "make the code change"
- "implement this in code"
- "update the files"
- "patch this"

## User Ownership

The user is responsible for application code decisions. AI may propose code and explain tradeoffs, but should not implement meaningful behavior without a second confirmation after the specific change is clear.

## Code As Last Resort

Writing application code should be the last resort after:

1. Clarifying the design decision.
2. Checking existing repo docs and Obsidian notes when relevant.
3. Considering whether an existing library or package is better suited to the problem.
4. Offering examples or pseudocode when that is enough to unblock the user.

When a well-supported library fits the task, recommend the library-first path and name the fallback plan if KitchenSync later outgrows or rejects that dependency.

Documentation and harmless boilerplate are exempt from this restriction.

## Practical Rule

If a change would affect how KitchenSync runs, stores data, validates data, parses recipes, indexes data, or exposes APIs, ask before editing.

Tests are support work: AI tools may write or update focused tests directly unless the test defines new product behavior or settles an unresolved design decision.

Environment management is support work: AI tools may use `uv` to add or update development dependencies and test tooling. Ask before changing runtime dependencies or application behavior.
