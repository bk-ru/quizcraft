# Repository instructions

## Working mode
- Work only within the requested task scope.
- Before editing, inspect the relevant files and identify the minimal set of changes required.
- Do not perform unrelated refactors.
- Preserve backward compatibility unless the task explicitly allows breaking changes.

## Code quality
- Enforce security checks and explicit error handling in all touched layers.
- Prefer DRY abstractions when repetition is real and stable.
- Use OOP where it improves clarity and responsibility boundaries.
- Prefer registries and mappings over long if/elif chains.
- Do not add code comments. Only docstrings are allowed.
- Use logging, never print.
- Avoid silent fallbacks unless explicitly required.

## Tests
- Add or update pytest tests for positive and negative scenarios for every behavior change.
- Do not finish the task without running relevant tests.
- If tests cannot be run, explain exactly why.

## Dependencies
- Do not add new production dependencies unless strictly necessary.
- If a new dependency is required, explain why the standard library or existing stack is insufficient.

## Output format
- At the end, provide:
  1. summary of changes,
  2. list of touched files,
  3. tests/linters/type checks run,
  4. known limitations,
  5. suggested commit message.

## Git
- Create one commit per completed task.
- Use Conventional Commits format:
  <type>(<scope>): <short description>
- Keep commits atomic.

## Planning and execution
- For multi-step work, plan before coding.
- Group remaining backlog into small implementation stages.
- Each stage must produce a reviewable increment.
- Each commit must be atomic and map to one logical change group.
- Do not mix unrelated layers in the same commit.
- Before implementation, identify dependencies and the minimal next stage.

## Commit policy
- Use focused commits only.
- Use Conventional Commits.
- Do not stage everything at once.
- Prefer separate commits for feat / test / docs / refactor when they are logically independent.